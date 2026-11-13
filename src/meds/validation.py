"""Dataset-level validation and quality-control checks for MEDS datasets.

The schema classes in :mod:`meds.schema` (via ``flexible_schema``) validate the *structure* of a single
table -- column names, dtypes, and nullability. They cannot capture constraints that span rows, shards, or
files, yet several such constraints are part of the MEDS specification:

1.  Data about a single subject cannot be split across parquet files.
2.  Data about a single subject must be contiguous within a parquet file and sorted by time (with
    static, null-time measurements first).
3.  Every code observed in the data must be present in ``metadata/codes.parquet``.

This module implements those checks, plus temporal-consistency checks around the special
``MEDS_BIRTH``/``MEDS_DEATH`` codes (no events before birth, no events after death), vocabulary-coverage
reporting, and validation of the on-disk metadata files. It is intended to run in CI over a freshly
produced MEDS dataset, or interactively while developing an ETL.

The main entry points are :func:`validate_data_shard` (a single in-memory ``pyarrow.Table``) and
:func:`validate_dataset` (a full ``$MEDS_ROOT`` directory on disk). A command-line interface is
exposed as the ``meds-validate`` console script::

    meds-validate /path/to/meds_dataset

The process exits with code 0 when every check passes and 1 otherwise, and prints a PASS/FAIL line per
check, so it can be used directly as a CI step.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from meds.schema import (
    CodeMetadataSchema,
    DataSchema,
    DatasetMetadataSchema,
    SubjectSplitSchema,
    birth_code,
    code_metadata_filepath,
    data_subdirectory,
    dataset_metadata_filepath,
    death_code,
    subject_splits_filepath,
)

#: Maximum number of offending examples (subject ids, codes, ...) reported per failed check.
_MAX_EXAMPLES = 5


@dataclass
class CheckResult:
    """The outcome of a single validation check.

    Attributes:
        name: Stable, machine-readable identifier for the check (e.g. ``"subject_contiguity"``).
        passed: Whether the check passed.
        message: Human-readable detail. Empty when the check passed.
        skipped: Whether the check was skipped because a prerequisite check failed.
    """

    name: str
    passed: bool
    message: str = ""
    skipped: bool = False

    def __str__(self) -> str:
        status = "SKIP" if self.skipped else "PASS" if self.passed else "FAIL"
        line = f"[{status}] {self.name}"
        if self.message:
            line += f": {self.message}"
        return line


@dataclass
class ValidationReport:
    """The aggregated outcome of validating a MEDS dataset or shard.

    Attributes:
        checks: The individual check results, in the order they were run.
        stats: Summary statistics collected during validation (subjects, events, shards, codes).
    """

    checks: list[CheckResult] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True when every non-skipped check passed."""
        return all(c.passed for c in self.checks if not c.skipped)

    @property
    def failed(self) -> list[CheckResult]:
        """The checks that failed."""
        return [c for c in self.checks if not c.passed and not c.skipped]

    def __str__(self) -> str:
        lines = [str(c) for c in self.checks]
        n_failed = len(self.failed)
        if self.stats:
            stat_str = ", ".join(f"{k}={v}" for k, v in self.stats.items())
            lines.append(f"stats: {stat_str}")
        lines.append(f"result: {'PASS' if self.passed else f'FAIL ({n_failed} failing checks)'}")
        return "\n".join(lines)


def _examples(items: list, max_examples: int = _MAX_EXAMPLES) -> str:
    """Render up to ``max_examples`` items, noting how many more were omitted."""
    shown = ", ".join(repr(i) for i in items[:max_examples])
    if len(items) > max_examples:
        shown += f", ... (+{len(items) - max_examples} more)"
    return shown


def _subject_run_boundaries(subject_ids: pa.Int64Array) -> list[int]:
    """Return row indices at which a new subject run starts, plus the table length.

    For example, ``[1, 1, 2, 2, 2, 1]`` is *not* contiguous and yields ``[0, 2, 5, 6]``; a contiguous
    column yields one boundary per distinct subject.
    """
    n = len(subject_ids)
    if n == 0:
        return [0]
    diff = pc.not_equal(subject_ids.slice(1), subject_ids.slice(0, n - 1))
    starts = pc.indices_nonzero(diff).to_pylist()
    return [0, *(int(s) + 1 for s in starts), n]


def _check_schema_conformance(tbl: pa.Table, shard_name: str) -> CheckResult:
    name = "shard_schema_conformance"
    try:
        DataSchema.validate(tbl)
    except Exception as e:
        return CheckResult(name=name, passed=False, message=f"{shard_name}: {e}")
    return CheckResult(name=name, passed=True)


def _check_subject_contiguity(
    tbl: pa.Table, subject_ids: pa.ChunkedArray, boundaries: list[int], shard_name: str
) -> CheckResult:
    name = "subject_contiguity"
    n_runs = len(boundaries) - 1
    n_subjects = pc.count_distinct(subject_ids).as_py()
    if n_runs == n_subjects:
        return CheckResult(name=name, passed=True)

    # Identify subjects whose rows are split across multiple runs.
    flat = subject_ids.combine_chunks()
    run_reps = [flat[b].as_py() for b in boundaries[:-1]]
    counts = pc.value_counts(pa.array(run_reps, type=pa.int64()))
    offenders = [row["values"] for row in counts.to_pylist() if row["counts"] > 1]
    return CheckResult(
        name=name,
        passed=False,
        message=(
            f"{shard_name}: {len(offenders)} subject(s) are split across non-contiguous row "
            f"blocks (examples: {_examples(offenders)})"
        ),
    )


def _check_subject_time_ordering(tbl: pa.Table, times: pa.ChunkedArray, shard_name: str) -> CheckResult:
    """Check that, within each subject, times are non-decreasing with nulls only first.

    Static (null-time) measurements must precede all timestamped events; timestamped events must be
    sorted ascending. Fully vectorized: adjacent row pairs are compared in bulk, and pairs that
    straddle a subject boundary are masked out.
    """
    name = "subject_time_ordering"
    n = tbl.num_rows
    if n < 2:
        return CheckResult(name=name, passed=True)

    sids = tbl.column("subject_id").combine_chunks()
    flat_times = times.combine_chunks()

    # True for adjacent pairs that start a new subject run; those pairs are not comparable.
    run_break = pc.not_equal(sids.slice(1), sids.slice(0, n - 1))
    prev, cur = flat_times.slice(0, n - 1), flat_times.slice(1)
    # A pair is fine if the previous time is null (static prefix) or prev <= cur.
    # Note: nulls are filled *before* the disjunction because pyarrow's ``or_`` propagates
    # null instead of applying Kleene logic, which would misclassify a null ``prev``.
    ok = pc.or_(pc.fill_null(pc.less_equal(prev, cur), False), pc.is_null(prev))
    bad = pc.and_(pc.invert(run_break), pc.invert(ok))
    bad_idx = pc.indices_nonzero(bad).to_pylist()

    if bad_idx:
        bad_sids = sorted(pc.unique(pc.take(sids.slice(1), pa.array(bad_idx))).to_pylist())
        return CheckResult(
            name=name,
            passed=False,
            message=(
                f"{shard_name}: {len(bad_sids)} subject(s) have out-of-order or misplaced "
                f"null-time events (examples: {_examples(bad_sids)})"
            ),
        )
    return CheckResult(name=name, passed=True)


def _check_birth_death_ordering(
    tbl: pa.Table, times: pa.ChunkedArray, codes: pa.ChunkedArray, shard_name: str
) -> list[CheckResult]:
    """Check MEDS_BIRTH/MEDS_DEATH temporal consistency per subject.

    - At most one birth and one death event per subject.
    - No timestamped event strictly before birth, none strictly after death.
    - Birth (when timestamped) is not after death.

    Fully vectorized: per-subject birth/death times are broadcast to every row of that subject via
    a dictionary-encoded subject index, so all comparisons run as bulk ``pyarrow.compute`` kernels.
    """
    birth_result = CheckResult(name="birth_event_ordering", passed=True)
    death_result = CheckResult(name="death_event_ordering", passed=True)

    flat_times = times.combine_chunks()
    flat_codes = codes.combine_chunks()
    sids = tbl.column("subject_id").combine_chunks()

    is_birth = pc.equal(flat_codes, birth_code)
    is_death = pc.equal(flat_codes, death_code)
    time_valid = pc.is_valid(flat_times)
    is_event = pc.and_(pc.invert(is_birth), pc.invert(is_death))
    event_mask = pc.and_(is_event, time_valid)

    def dup_offenders(mask: pa.BooleanArray) -> list[tuple[int, int]]:
        vc = pc.value_counts(pc.filter(sids, mask)).to_pylist()
        return [(row["values"], row["counts"]) for row in vc if row["counts"] > 1]

    def offender_subjects(mask: pa.BooleanArray) -> list[int]:
        idx = pc.indices_nonzero(mask).to_pylist()
        if not idx:
            return []
        return sorted(pc.unique(pc.take(sids, pa.array(idx))).to_pylist())

    def broadcast_times(mask: pa.BooleanArray) -> pa.Array:
        """Broadcast each subject's single matching timestamp to all of its rows."""
        enc = pc.dictionary_encode(sids)
        per_subject: list = [None] * len(enc.dictionary)
        positions = pc.filter(enc.indices, mask).to_pylist()
        stamps = pc.filter(flat_times, mask).to_pylist()
        for p, t in zip(positions, stamps, strict=True):
            per_subject[p] = t
        return pc.take(pa.array(per_subject, type=pa.timestamp("us")), enc.indices)

    birth_problems: list[str] = []
    death_problems: list[str] = []

    birth_dups = dup_offenders(is_birth)
    death_dups = dup_offenders(is_death)
    birth_problems.extend(f"subject {sid}: {n} MEDS_BIRTH events" for sid, n in birth_dups)
    death_problems.extend(f"subject {sid}: {n} MEDS_DEATH events" for sid, n in death_dups)

    # Temporal comparisons are only meaningful when there is at most one birth/death per subject.
    if not birth_dups:
        birth_per_row = broadcast_times(pc.and_(is_birth, time_valid))
        before_birth = pc.and_(event_mask, pc.less(flat_times, birth_per_row))
        for sid in offender_subjects(before_birth):
            birth_problems.append(f"subject {sid}: event(s) before MEDS_BIRTH")
    if not death_dups:
        death_per_row = broadcast_times(pc.and_(is_death, time_valid))
        after_death = pc.and_(event_mask, pc.greater(flat_times, death_per_row))
        for sid in offender_subjects(after_death):
            death_problems.append(f"subject {sid}: event(s) after MEDS_DEATH")
    if not birth_dups and not death_dups:
        birth_per_row = broadcast_times(pc.and_(is_birth, time_valid))
        death_per_row = broadcast_times(pc.and_(is_death, time_valid))
        birth_after_death = pc.and_(pc.and_(is_birth, time_valid), pc.greater(birth_per_row, death_per_row))
        for sid in offender_subjects(birth_after_death):
            birth_problems.append(f"subject {sid}: MEDS_BIRTH after MEDS_DEATH")

    if birth_problems:
        birth_result = CheckResult(
            name=birth_result.name, passed=False, message=f"{shard_name}: {_examples(birth_problems)}"
        )
    if death_problems:
        death_result = CheckResult(
            name=death_result.name, passed=False, message=f"{shard_name}: {_examples(death_problems)}"
        )
    return [birth_result, death_result]


def validate_data_shard(tbl: pa.Table, shard_name: str = "<table>") -> list[CheckResult]:
    """Validate a single MEDS data shard (an in-memory ``pyarrow.Table``).

    Runs, in order: schema conformance, subject contiguity, per-subject time ordering, and
    MEDS_BIRTH/MEDS_DEATH temporal consistency. Per-subject checks are skipped when subject
    contiguity fails, since subject runs are ill-defined in that case.

    Args:
        tbl: The shard contents. Must conform to :class:`meds.DataSchema`.
        shard_name: Label used in check messages (e.g. the parquet file path).

    Returns:
        The list of :class:`CheckResult` objects, in run order.
    """
    checks = [_check_schema_conformance(tbl, shard_name)]
    if not checks[0].passed:
        for name in (
            "subject_contiguity",
            "subject_time_ordering",
            "birth_event_ordering",
            "death_event_ordering",
        ):
            checks.append(
                CheckResult(
                    name=name,
                    passed=False,
                    skipped=True,
                    message="skipped: shard does not conform to DataSchema",
                )
            )
        return checks

    subject_ids = tbl.column("subject_id")
    times = tbl.column("time")
    codes = tbl.column("code")
    boundaries = _subject_run_boundaries(subject_ids.combine_chunks())

    contiguity = _check_subject_contiguity(tbl, subject_ids, boundaries, shard_name)
    checks.append(contiguity)
    if not contiguity.passed:
        for name in ("subject_time_ordering", "birth_event_ordering", "death_event_ordering"):
            checks.append(
                CheckResult(
                    name=name, passed=False, skipped=True, message="skipped: subjects are not contiguous"
                )
            )
        return checks

    checks.append(_check_subject_time_ordering(tbl, times, shard_name))
    checks.extend(_check_birth_death_ordering(tbl, times, codes, shard_name))
    return checks


def _read_parquet_table(path: Path) -> pa.Table:
    return pq.read_table(path)


def _validate_metadata_files(meds_root: Path) -> tuple[list[CheckResult], dict]:
    """Validate the ``metadata/`` files that must (or may) accompany a MEDS dataset."""
    checks: list[CheckResult] = []
    info: dict = {}

    dataset_json = meds_root / dataset_metadata_filepath
    if not dataset_json.is_file():
        checks.append(
            CheckResult(
                name="dataset_metadata_present", passed=False, message=f"missing {dataset_metadata_filepath}"
            )
        )
    else:
        checks.append(CheckResult(name="dataset_metadata_present", passed=True))
        try:
            metadata = json.loads(dataset_json.read_text())
            DatasetMetadataSchema.validate(metadata)
            checks.append(CheckResult(name="dataset_metadata_valid", passed=True))
        except Exception as e:
            checks.append(CheckResult(name="dataset_metadata_valid", passed=False, message=str(e)))

    codes_path = meds_root / code_metadata_filepath
    meta_codes: set[str] = set()
    if not codes_path.is_file():
        checks.append(
            CheckResult(
                name="code_metadata_present", passed=False, message=f"missing {code_metadata_filepath}"
            )
        )
        checks.append(
            CheckResult(
                name="code_metadata_valid",
                passed=False,
                skipped=True,
                message="skipped: code metadata file missing",
            )
        )
    else:
        checks.append(CheckResult(name="code_metadata_present", passed=True))
        try:
            code_tbl = _read_parquet_table(codes_path)
            CodeMetadataSchema.validate(code_tbl)
            meta_codes = set(pc.drop_null(code_tbl.column("code")).to_pylist())
            info["n_metadata_codes"] = len(meta_codes)
            checks.append(CheckResult(name="code_metadata_valid", passed=True))
        except Exception as e:
            checks.append(CheckResult(name="code_metadata_valid", passed=False, message=str(e)))

    splits_path = meds_root / subject_splits_filepath
    split_subjects: set[int] = set()
    if not splits_path.is_file():
        checks.append(
            CheckResult(
                name="subject_splits_valid",
                passed=False,
                skipped=True,
                message=f"optional file {subject_splits_filepath} not present",
            )
        )
        checks.append(
            CheckResult(
                name="subject_splits_subjects_known",
                passed=False,
                skipped=True,
                message="skipped: no subject splits file",
            )
        )
    else:
        try:
            splits_tbl = _read_parquet_table(splits_path)
            SubjectSplitSchema.validate(splits_tbl)
            split_subjects = set(splits_tbl.column("subject_id").to_pylist())
            n_unique = pc.count_distinct(splits_tbl.column("subject_id")).as_py()
            if n_unique != len(split_subjects):
                checks.append(
                    CheckResult(
                        name="subject_splits_valid",
                        passed=False,
                        message="duplicate subject_id rows in subject splits file",
                    )
                )
            else:
                checks.append(CheckResult(name="subject_splits_valid", passed=True))
                info["n_split_subjects"] = len(split_subjects)
        except Exception as e:
            checks.append(CheckResult(name="subject_splits_valid", passed=False, message=str(e)))
            checks.append(
                CheckResult(
                    name="subject_splits_subjects_known",
                    passed=False,
                    skipped=True,
                    message="skipped: subject splits file invalid",
                )
            )

    info["meta_codes"] = meta_codes
    info["split_subjects"] = split_subjects
    return checks, info


def validate_dataset(meds_root: str | Path, *, fail_fast: bool = False) -> ValidationReport:
    """Validate a full MEDS dataset rooted at ``meds_root``.

    Discovers all ``data/**/*.parquet`` shards, runs :func:`validate_data_shard` on each, then runs
    dataset-level checks: no subject may appear in more than one shard, every code observed in the
    data must be listed in ``metadata/codes.parquet``, and the metadata files must exist and
    conform to their schemas. Subjects referenced by ``metadata/subject_splits.parquet`` (when
    present) must exist in the data.

    Args:
        meds_root: Path to the root of the MEDS dataset.
        fail_fast: Stop after the first failing check instead of running all checks.

    Returns:
        A :class:`ValidationReport` with per-check results and summary statistics.
    """
    meds_root = Path(meds_root)
    report = ValidationReport()

    def add(check: CheckResult) -> bool:
        report.checks.append(check)
        return not fail_fast or check.passed or check.skipped

    shard_paths = sorted((meds_root / data_subdirectory).rglob("*.parquet"))
    if not shard_paths:
        report.checks.append(
            CheckResult(
                name="shard_discovery",
                passed=False,
                message=f"no parquet files found under {meds_root / data_subdirectory}",
            )
        )
        return report
    report.checks.append(
        CheckResult(name="shard_discovery", passed=True, message=f"found {len(shard_paths)} shard(s)")
    )
    report.stats["n_shards"] = len(shard_paths)

    all_subjects: set[int] = set()
    all_codes: set[str] = set()
    n_events = 0
    subjects_check_ok = True

    for shard_path in shard_paths:
        rel = str(shard_path.relative_to(meds_root))
        try:
            tbl = _read_parquet_table(shard_path)
        except Exception as e:
            report.checks.append(CheckResult(name="shard_readable", passed=False, message=f"{rel}: {e}"))
            if fail_fast:
                return report
            continue
        report.checks.append(CheckResult(name="shard_readable", passed=True, message=rel))

        for check in validate_data_shard(tbl, shard_name=rel):
            if not add(check):
                return report

        n_events += tbl.num_rows
        try:
            shard_subjects = set(pc.unique(tbl.column("subject_id")).to_pylist())
            shard_codes = set(pc.drop_null(pc.unique(tbl.column("code"))).to_pylist())
        except Exception as e:
            report.checks.append(
                CheckResult(name="shard_subject_enumeration", passed=False, message=f"{rel}: {e}")
            )
            if fail_fast:
                return report
            continue

        overlap = all_subjects & shard_subjects
        if overlap:
            subjects_check_ok = False
            report.checks.append(
                CheckResult(
                    name="subject_shard_exclusivity",
                    passed=False,
                    message=(
                        f"{rel}: {len(overlap)} subject(s) already seen in another shard "
                        f"(examples: {_examples(sorted(overlap))})"
                    ),
                )
            )
            if fail_fast:
                return report
        all_subjects |= shard_subjects
        all_codes |= shard_codes

    if subjects_check_ok:
        report.checks.append(CheckResult(name="subject_shard_exclusivity", passed=True))

    report.stats["n_subjects"] = len(all_subjects)
    report.stats["n_events"] = n_events
    report.stats["n_data_codes"] = len(all_codes)

    metadata_checks, meta_info = _validate_metadata_files(meds_root)
    for check in metadata_checks:
        if not add(check):
            return report

    meta_codes: set[str] = meta_info["meta_codes"]
    if meta_codes or all_codes:
        missing = sorted(all_codes - meta_codes)
        if missing:
            report.checks.append(
                CheckResult(
                    name="code_vocabulary_coverage",
                    passed=False,
                    message=(
                        f"{len(missing)} code(s) observed in data but missing from "
                        f"{code_metadata_filepath} (examples: {_examples(missing)})"
                    ),
                )
            )
        else:
            report.checks.append(CheckResult(name="code_vocabulary_coverage", passed=True))
        report.stats["vocabulary_coverage"] = (
            f"{len(all_codes)}/{len(meta_codes)} metadata codes observed in data"
        )

    split_subjects: set[int] = meta_info["split_subjects"]
    if split_subjects:
        unknown = sorted(split_subjects - all_subjects)
        if unknown:
            report.checks.append(
                CheckResult(
                    name="subject_splits_subjects_known",
                    passed=False,
                    message=(
                        f"{len(unknown)} split subject(s) not found in data (examples: {_examples(unknown)})"
                    ),
                )
            )
        else:
            # Only append a passing result if the check wasn't already recorded as skipped/failed.
            if not any(c.name == "subject_splits_subjects_known" and not c.skipped for c in report.checks):
                report.checks.append(CheckResult(name="subject_splits_subjects_known", passed=True))

    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``meds-validate [--fail-fast] MEDS_ROOT``."""
    parser = argparse.ArgumentParser(
        prog="meds-validate",
        description="Validate a MEDS dataset: schema conformance, subject sharding, time "
        "ordering, MEDS_BIRTH/MEDS_DEATH consistency, and code vocabulary coverage.",
    )
    parser.add_argument("meds_root", help="Root directory of the MEDS dataset to validate.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failing check.")
    args = parser.parse_args(argv)

    report = validate_dataset(args.meds_root, fail_fast=args.fail_fast)
    print(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
