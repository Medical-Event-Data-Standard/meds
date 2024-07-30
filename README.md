# Medical Event Data Standard

The Medical Event Data Standard (MEDS) is a data schema for storing streams of medical events, often
sourced from either Electronic Health Records or claims records. Before we define the various schema that make
up MEDS, we will define some key terminology that we use in this standard.

## Terminology
  1. A _patient_ in a MEDS dataset is the primary entity being described by the sequences of care observations
     in the underlying dataset. In most cases, _patients_ will, naturally, be individuals, and the sequences
     of care observations will cover all known observations about those individuals in a source health
     datasets. However, in some cases, data may be organized so that we cannot describe all the data for an
     individual reliably in a dataset, but instead can only describe subsequences of an individual's data,
     such as in datasets that only link an individual's data observations together if they are within the same
     hospital admission, regardless of how many admissions that individual has in the dataset (such as the
     [eICU](https://eicu-crd.mit.edu/) dataset). In these cases, a _patient_ in the MEDS dataset may refer to
     a hospital admission rather than an individual.
  2. A _code_ is the categorical descriptor of what is being observed in any given observation of a patient.
     In particular, in almost all structured, longitudinal datasets, a measurement can be described as
     consisting of a tuple containing a `patient_id` (who this measurement is about); a `timestamp` (when this
     measurement happened); some categorical qualifier describing what was measured, which we will call a
     `code`; a value of a given type, such as a `numerical_value`, a `text_value`, or a `categorical_value`;
     and possibly one or more additional measurement properties that describe the measurement in a
     non-standardized manner.

## Core MEDS Data Organization

MEDS consists of four main data components/schemas:
  1. A _data schema_. This schema describes the underlying medical data, organized as sequences of patient
     observations, in the dataset.
  2. A _patient subsequence label schema_. This schema describes labels that may be predicted about a patient
     at a given timestamp in the patient record.
  3. A _code metadata schema_. This schema contains metadata describing the codes used to categorize the
     observed measurements in the dataset.
  4. A _dataset metadata schema_. This schema contains metadata about the MEDS dataset itself, such as when it
     was produced, using what version of what code, etc.
  5. A _patient split schema_. This schema contains metadata about how patients in the MEDS dataset are
     assigned to different subpopulations, most commonly used to dictate ML splits.

### Organization on Disk
Given a MEDS dataset stored in the `$MEDS_ROOT` directory data of the various schemas outlined above can be
found in the following subfolders:
  - `$MEDS_ROOT/data/`: This directory will contain data in the _data schema_, organized as a
    series of possibly nested sharded dataframes stored in `parquet` files. In particular, the file glob
    `glob("$MEDS_ROOT/data/**/*.parquet)` will capture all sharded data files of the raw MEDS data, all
    organized into _data schema_ files, sharded by patient and sorted, for each patient, by
    timestamp.
  - `$MEDS_ROOT/metadata/codes.parquet`: This file contains per-code metadata in the _code metadata schema_
    about the MEDS dataset. As this dataset describes all codes observed in the full MEDS dataset, it is _not_
    sharded. Note that some pre-processing operations may, at times, produce sharded code metadata files, but
    these will always appear in subdirectories of `$MEDS_ROOT/metadata/` rather than at the top level, and
    should generally not be used for overall metadata operations.
  - `$MEDS_ROOT/metadata/dataset.json`: This schema contains metadata in the _dataset metadata schema_ about
    the dataset and its production process.
  - `$MEDS_ROOT/metdata/patient_splits.parquet`: This schema contains information in the _patient split
    schema_ about what splits different patients are in.

Task label dataframes are stored in the _TODO label_ schema, in a file path that depends on both a
`$TASK_ROOT` directory where task label dataframes are stored and a `$TASK_NAME` parameter that separates
different tasks from one another. In particular, the file glob `glob($TASK_ROOT/$TASK_NAME/**/*.parquet)` will
retrieve a sharded set of dataframes in the _TODO label_ schema where the sharding matches up precisely with
the sharding used in the raw `$MEDS_ROOT/data/**/*.parquet` files (e.g., the file
`$TASK_ROOT/$TASK_NAME/$SHARD_NAME.parquet` will cover the labels for the same set of patients as are
contained in the raw data file at `$MEDS_ROOT/data/**/*.parquet`). Note that (1) `$TASK_ROOT` may be a subdir
of `$MEDS_ROOT` (e.g., often `$TASK_ROOT` will be set to `$MEDS_ROOT/tasks`), (2) `$TASK_NAME` may have `/`s
in it, thereby rendering the task label directory a deep, nested subdir of `$TASK_ROOT`, and (3) in some
cases, there may be no task labels for a shard of the raw data, if no patient in that shard qualifies for that
task, in which case it may be true that either `$TASK_ROOT/$TASK_NAME/$SHARD_NAME.parquet` is empty or that it
does not exist.

### Schemas

**TODO**: copy here from the schema file and describe.






## Old -- to be deleted.

The core of the standard is that we define a ``patient`` data structure that contains a series of time stamped events, that in turn contain measurements of various sorts.

The Python type signature for the schema is as follows:

```python

Patient = TypedDict('Patient', {
  'patient_id': int,
  'events': List[Event],
})

Event = TypedDict('Event',{
    'time': NotRequired[datetime.datetime], # Static events will have a null timestamp here
    'code': str,
    'text_value': NotRequired[str],
    'numeric_value': NotRequired[float],
    'datetime_value': NotRequired[datetime.datetime],
    'metadata': NotRequired[Mapping[str, Any]],
})
```

We also provide ETLs to convert common data formats to this schema: https://github.com/Medical-Event-Data-Standard/meds_etl

An example patient following this schema

```python

patient_data = {
  "patient_id": 123,
  "events": [
    # Store static events like gender with a null timestamp
    {
        "time": None,
        "code": "Gender/F",
    },

    # It's recommended to record birth using the birth_code
    {
      "time": datetime.datetime(1995, 8, 20),
      "code": meds.birth_code,
    },

    # Arbitrary events with sophisticated data can also be added
    {
        "time": datetime.datetime(2020, 1, 1, 12, 0, 0),
        "code": "some_code",
        "text_value": "Example",
        "numeric_value": 10.0,
        "datetime_value": datetime.datetime(2020, 1, 1, 12, 0, 0),
        "properties": None
    },
  ]
}

```
