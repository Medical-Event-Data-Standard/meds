import datetime

import pyarrow as pa
import pyarrow.parquet as pq

from meds import (
    CheckResult,
    ValidationReport,
    birth_code,
    death_code,
    validate_data_shard,
    validate_dataset,
)
from meds.validation import main

DATA_SCHEMA = pa.schema(
    [
        pa.field("subject_id", pa.int64(), nullable=False),
        pa.field("time", pa.timestamp("us"), nullable=True),
        pa.field("code", pa.string(), nullable=False),
        pa.field("numeric_value", pa.float32(), nullable=True),
        pa.field("text_value", pa.large_string(), nullable=True),
    ]
)


def dt(y, m, d, h=0, mi=0):
    return datetime.datetime(y, m, d, h, mi)


def make_shard(rows):
    return pa.Table.from_pylist(rows, schema=DATA_SCHEMA)


def valid_subject_rows(sid, birth=None, events=True):
    birth = dt(2020, 1, 1) if birth is None else birth
    rows = [
        {"subject_id": sid, "time": None, "code": "GENDER//F", "numeric_value": None, "text_value": None},
        {"subject_id": sid, "time": birth, "code": birth_code, "numeric_value": None, "text_value": None},
    ]
    if events:
        rows += [
            {
                "subject_id": sid,
                "time": birth + datetime.timedelta(days=10),
                "code": "LAB//123",
                "numeric_value": 1.5,
                "text_value": None,
            },
            {
                "subject_id": sid,
                "time": birth + datetime.timedelta(days=20),
                "code": "DX//456",
                "numeric_value": None,
                "text_value": "note",
            },
        ]
    return rows


def check_by_name(checks, name):
    matches = [c for c in checks if c.name == name]
    assert len(matches) == 1, f"expected one check named {name}, got {len(matches)}"
    return matches[0]


def assert_all_pass(checks):
    failed = [c for c in checks if not c.passed and not c.skipped]
    assert not failed, "expected all checks to pass, failed: " + "; ".join(str(c) for c in failed)


def test_valid_shard_passes():
    tbl = make_shard(valid_subject_rows(1) + valid_subject_rows(2))
    checks = validate_data_shard(tbl, shard_name="0.parquet")
    assert_all_pass(checks)
    assert {c.name for c in checks} == {
        "shard_schema_conformance",
        "subject_contiguity",
        "subject_time_ordering",
        "birth_event_ordering",
        "death_event_ordering",
    }


def test_empty_shard_passes():
    tbl = make_shard([])
    assert_all_pass(validate_data_shard(tbl))


def test_unsorted_times_fail():
    rows = valid_subject_rows(1)
    rows[2], rows[3] = rows[3], rows[2]  # swap two timestamped events
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "subject_time_ordering")
    assert not check.passed
    assert "1" in check.message  # offending subject id reported


def test_null_time_after_timestamped_event_fails():
    rows = valid_subject_rows(1)
    rows.append(
        {"subject_id": 1, "time": None, "code": "STATIC//X", "numeric_value": None, "text_value": None}
    )
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "subject_time_ordering")
    assert not check.passed


def test_noncontiguous_subject_fails_and_skips_dependent_checks():
    s1 = valid_subject_rows(1, events=False)
    s2 = valid_subject_rows(2, events=False)
    # Interleave the two subjects so both are split across non-contiguous blocks.
    rows = [s1[0], s2[0], s1[1], s2[1]]
    tbl = make_shard(rows)
    checks = validate_data_shard(tbl)
    contiguity = check_by_name(checks, "subject_contiguity")
    assert not contiguity.passed
    assert "1" in contiguity.message
    for name in ("subject_time_ordering", "birth_event_ordering", "death_event_ordering"):
        check = check_by_name(checks, name)
        assert check.skipped


def test_event_before_birth_fails():
    rows = valid_subject_rows(1)
    rows.insert(
        2,
        {
            "subject_id": 1,
            "time": dt(2019, 12, 31),
            "code": "LAB//999",
            "numeric_value": 0.1,
            "text_value": None,
        },
    )
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "birth_event_ordering")
    assert not check.passed
    assert "before MEDS_BIRTH" in check.message


def test_event_after_death_fails():
    rows = valid_subject_rows(1)
    death_time = dt(2020, 6, 1)
    rows.append(
        {"subject_id": 1, "time": death_time, "code": death_code, "numeric_value": None, "text_value": None}
    )
    rows.append(
        {
            "subject_id": 1,
            "time": dt(2020, 7, 1),
            "code": "LAB//999",
            "numeric_value": 0.1,
            "text_value": None,
        }
    )
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "death_event_ordering")
    assert not check.passed
    assert "after MEDS_DEATH" in check.message


def test_valid_death_at_end_passes():
    rows = valid_subject_rows(1)
    rows.append(
        {
            "subject_id": 1,
            "time": dt(2020, 6, 1),
            "code": death_code,
            "numeric_value": None,
            "text_value": None,
        }
    )
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "death_event_ordering")
    assert check.passed


def test_duplicate_birth_fails():
    rows = valid_subject_rows(1)
    rows.append(
        {
            "subject_id": 1,
            "time": dt(2020, 2, 1),
            "code": birth_code,
            "numeric_value": None,
            "text_value": None,
        }
    )
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "birth_event_ordering")
    assert not check.passed


def test_birth_after_death_fails():
    rows = [
        {"subject_id": 1, "time": None, "code": "GENDER//F", "numeric_value": None, "text_value": None},
        {
            "subject_id": 1,
            "time": dt(2020, 6, 1),
            "code": death_code,
            "numeric_value": None,
            "text_value": None,
        },
        {
            "subject_id": 1,
            "time": dt(2020, 7, 1),
            "code": birth_code,
            "numeric_value": None,
            "text_value": None,
        },
    ]
    tbl = make_shard(rows)
    check = check_by_name(validate_data_shard(tbl), "birth_event_ordering")
    assert not check.passed


def test_schema_violation_fails_and_skips_rest():
    tbl = pa.table(
        {
            "subject_id": pa.array([1, 2], type=pa.int64()),
            "time": pa.array([dt(2020, 1, 1), dt(2020, 1, 2)], type=pa.timestamp("us")),
            # missing required "code" column
        }
    )
    checks = validate_data_shard(tbl)
    assert not check_by_name(checks, "shard_schema_conformance").passed
    for name in (
        "subject_contiguity",
        "subject_time_ordering",
        "birth_event_ordering",
        "death_event_ordering",
    ):
        assert check_by_name(checks, name).skipped


# ---------------------------------------------------------------------------
# On-disk dataset tests
# ---------------------------------------------------------------------------

ALL_CODES = ["GENDER//F", birth_code, death_code, "LAB//123", "DX//456"]


def write_meds_dataset(root, shard_rows, codes=ALL_CODES, with_splits=True, with_dataset_json=True):
    """Write a minimal MEDS dataset directory tree under ``root``.

    ``shard_rows`` maps a relative shard path (e.g. ``"train/0.parquet"``) to row dicts.
    """
    for rel, rows in shard_rows.items():
        path = root / "data" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(make_shard(rows), path)

    meta = root / "metadata"
    meta.mkdir(parents=True, exist_ok=True)
    if with_dataset_json:
        (meta / "dataset.json").write_text(
            '{"dataset_name": "test", "dataset_version": "0.1", "etl_name": "test-etl"}'
        )
    pq.write_table(
        pa.table(
            {
                "code": pa.array(codes, type=pa.string()),
                "description": pa.array([None] * len(codes), type=pa.string()),
                "parent_codes": pa.array([None] * len(codes), type=pa.list_(pa.string())),
            }
        ),
        meta / "codes.parquet",
    )
    if with_splits:
        pq.write_table(
            pa.table(
                {
                    "subject_id": pa.array([1, 2, 3], type=pa.int64()),
                    "split": pa.array(["train", "train", "tuning"], type=pa.string()),
                }
            ),
            meta / "subject_splits.parquet",
        )


def valid_dataset_shards():
    return {
        "train/0.parquet": valid_subject_rows(1) + valid_subject_rows(2),
        "tuning/0.parquet": valid_subject_rows(3, birth=dt(2019, 5, 5)),
    }


def test_validate_dataset_valid(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards())
    report = validate_dataset(tmp_path)
    assert isinstance(report, ValidationReport)
    assert report.passed, "\n".join(str(c) for c in report.failed)
    assert report.stats["n_subjects"] == 3
    assert report.stats["n_shards"] == 2
    assert report.stats["n_events"] == 12
    assert "vocabulary_coverage" in report.stats
    assert "[PASS]" in str(report)


def test_validate_dataset_subject_across_shards_fails(tmp_path):
    shards = valid_dataset_shards()
    shards["tuning/0.parquet"] = shards["tuning/0.parquet"] + valid_subject_rows(
        1, birth=dt(2018, 1, 1), events=False
    )
    write_meds_dataset(tmp_path, shards)
    report = validate_dataset(tmp_path)
    assert not report.passed
    check = check_by_name(report.checks, "subject_shard_exclusivity")
    assert not check.passed
    assert "1" in check.message


def test_validate_dataset_missing_code_in_metadata_fails(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards(), codes=[c for c in ALL_CODES if c != "DX//456"])
    report = validate_dataset(tmp_path)
    assert not report.passed
    check = check_by_name(report.checks, "code_vocabulary_coverage")
    assert not check.passed
    assert "DX//456" in check.message


def test_validate_dataset_missing_dataset_json_fails(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards(), with_dataset_json=False)
    report = validate_dataset(tmp_path)
    assert not report.passed
    assert not check_by_name(report.checks, "dataset_metadata_present").passed


def test_validate_dataset_missing_codes_parquet_fails(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards())
    (tmp_path / "metadata" / "codes.parquet").unlink()
    report = validate_dataset(tmp_path)
    assert not report.passed
    assert not check_by_name(report.checks, "code_metadata_present").passed
    assert check_by_name(report.checks, "code_metadata_valid").skipped


def test_validate_dataset_unknown_split_subject_fails(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards())
    pq.write_table(
        pa.table(
            {
                "subject_id": pa.array([1, 2, 999], type=pa.int64()),
                "split": pa.array(["train", "train", "tuning"], type=pa.string()),
            }
        ),
        tmp_path / "metadata" / "subject_splits.parquet",
    )
    report = validate_dataset(tmp_path)
    assert not report.passed
    check = check_by_name(report.checks, "subject_splits_subjects_known")
    assert not check.passed
    assert "999" in check.message


def test_validate_dataset_no_splits_file_skips_split_checks(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards(), with_splits=False)
    report = validate_dataset(tmp_path)
    assert report.passed
    assert check_by_name(report.checks, "subject_splits_valid").skipped


def test_validate_dataset_no_shards_fails(tmp_path):
    (tmp_path / "data").mkdir()
    report = validate_dataset(tmp_path)
    assert not report.passed
    assert not check_by_name(report.checks, "shard_discovery").passed


def test_validate_dataset_bad_shard_fails(tmp_path):
    shards = valid_dataset_shards()
    rows = valid_subject_rows(3, birth=dt(2019, 5, 5))
    rows[2], rows[3] = rows[3], rows[2]
    shards["tuning/0.parquet"] = rows
    write_meds_dataset(tmp_path, shards)
    report = validate_dataset(tmp_path)
    assert not report.passed
    assert any(not c.passed and c.name == "subject_time_ordering" for c in report.checks)


def test_fail_fast_stops_early(tmp_path):
    write_meds_dataset(tmp_path, valid_dataset_shards(), with_dataset_json=False)
    full = validate_dataset(tmp_path)
    fast = validate_dataset(tmp_path, fail_fast=True)
    assert not fast.passed
    assert len(fast.checks) < len(full.checks)


def test_cli_main_valid_and_invalid(tmp_path, capsys):
    write_meds_dataset(tmp_path, valid_dataset_shards())
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "[PASS] shard_discovery" in out
    assert "result: PASS" in out

    bad = tmp_path / "bad"
    write_meds_dataset(bad, valid_dataset_shards(), with_dataset_json=False)
    assert main([str(bad)]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] dataset_metadata_present" in out
    assert "result: FAIL" in out


def test_checkresult_str():
    assert str(CheckResult(name="x", passed=True)) == "[PASS] x"
    assert str(CheckResult(name="x", passed=False, message="boom")) == "[FAIL] x: boom"
    assert str(CheckResult(name="x", passed=False, skipped=True)) == "[SKIP] x"
