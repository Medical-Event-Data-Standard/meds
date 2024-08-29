# Medical Event Data Standard

The Medical Event Data Standard (MEDS) is a data schema for storing streams of medical events, often
sourced from either Electronic Health Records or claims records. Before we define the various schema that make
up MEDS, we will define some key terminology that we use in this standard.

## Terminology
  1. A _subject_ in a MEDS dataset is the primary entity being described by the sequences of care observations
     in the underlying dataset. In most cases, _subjects_ will, naturally, be individuals, and the sequences
     of care observations will cover all known observations about those individuals in a source health
     datasets. However, in some cases, data may be organized so that we cannot describe all the data for an
     individual reliably in a dataset, but instead can only describe subsequences of an individual's data,
     such as in datasets that only link an individual's data observations together if they are within the same
     hospital admission, regardless of how many admissions that individual has in the dataset (such as the
     [eICU](https://eicu-crd.mit.edu/) dataset). In these cases, a _subject_ in the MEDS dataset may refer to
     a hospital admission rather than an individual.
  2. A _code_ is the categorical descriptor of what is being observed in any given observation of a subject.
     In particular, in almost all structured, longitudinal datasets, a measurement can be described as
     consisting of a tuple containing a `subject_id` (who this measurement is about); a `time` (when this
     measurement happened); some categorical qualifier describing what was measured, which we will call a
     `code`; a value of a given type, such as a `numeric_value`, a `text_value`, or a `categorical_value`;
     and possibly one or more additional measurement properties that describe the measurement in a
     non-standardized manner.

## Core MEDS Data Organization

MEDS consists of four main data components/schemas:
  1. A _data schema_. This schema describes the underlying medical data, organized as sequences of subject
     observations, in the dataset.
  2. A _subject subsequence label schema_. This schema describes labels that may be predicted about a subject
     at a given time in the subject record.
  3. A _code metadata schema_. This schema contains metadata describing the codes used to categorize the
     observed measurements in the dataset.
  4. A _dataset metadata schema_. This schema contains metadata about the MEDS dataset itself, such as when it
     was produced, using what version of what code, etc.
  5. A _subject split schema_. This schema contains metadata about how subjects in the MEDS dataset are
     assigned to different subpopulations, most commonly used to dictate ML splits.

### Organization on Disk
Given a MEDS dataset stored in the `$MEDS_ROOT` directory data of the various schemas outlined above can be
found in the following subfolders:
  - `$MEDS_ROOT/data/`: This directory will contain data in the _data schema_, organized as a
    series of possibly nested sharded dataframes stored in `parquet` files. In particular, the file glob
    `glob("$MEDS_ROOT/data/**/*.parquet)` will capture all sharded data files of the raw MEDS data, all
    organized into _data schema_ files, sharded by subject and sorted, for each subject, by
    time.
  - `$MEDS_ROOT/metadata/codes.parquet`: This file contains per-code metadata in the _code metadata schema_
    about the MEDS dataset. All codes within the dataset should have an entry in this file.
    As this dataset describes all codes observed in the full MEDS dataset, it is _not_
    sharded. Note that some pre-processing operations may, at times, produce sharded code metadata files, but
    these will always appear in subdirectories of `$MEDS_ROOT/metadata/` rather than at the top level, and
    should generally not be used for overall metadata operations.
  - `$MEDS_ROOT/metadata/dataset.json`: This schema contains metadata in the _dataset metadata schema_ about
    the dataset and its production process.
  - `$MEDS_ROOT/metdata/subject_splits.parquet`: This schema contains information in the _subject split
    schema_ about what splits different subjects are in.

Task label dataframes are stored in the `label_schema`, in a file path that depends on both a
`$TASK_ROOT` directory where task label dataframes are stored and a `$TASK_NAME` parameter that separates
different tasks from one another. In particular, the file glob `glob($TASK_ROOT/$TASK_NAME/**/*.parquet)` will
retrieve a sharded set of dataframes in the `label_schema` where the sharding may or may not match up with
the sharding used in the raw `$MEDS_ROOT/data/**/*.parquet` files (e.g., the file
`$TASK_ROOT/$TASK_NAME/$SHARD_NAME.parquet` may cover the labels for the same set of subjects as are
contained in the raw data file at `$MEDS_ROOT/data/**/*.parquet`). Note that (1) `$TASK_ROOT` may be a subdir
of `$MEDS_ROOT` (e.g., often `$TASK_ROOT` will be set to `$MEDS_ROOT/tasks`), (2) `$TASK_NAME` may have `/`s
in it, thereby rendering the task label directory a deep, nested subdir of `$TASK_ROOT`, and (3) in some
cases, there may be no task labels for a shard of the raw data, if no subject in that shard qualifies for that
task, in which case it may be true that either `$TASK_ROOT/$TASK_NAME/$SHARD_NAME.parquet` is empty or that it
does not exist.

### Schemas

#### The Data Schema
MEDS data also must satisfy two important properties:
  1. Data about a single subject cannot be split across parquet files. If a subject is in a dataset it must be
     in one and only one parquet file.
  2. Data about a single subject must be contiguous within a particular parquet file and sorted by time.

The data schema has four mandatory fields:
  1. `subject_id`: The ID of the subject this event is about.
  2. `time`: The time of the event. This field is nullable for static events.
  3. `code`: The code of the event.
  4. `numeric_value`: The numeric value of the event. This field is nullable for non-numeric events.

In addition, it can contain any number of custom properties to further enrich observations. The python
function below generates a pyarrow schema for a given set of custom properties.

```python
def data_schema(custom_properties=[]):
    return pa.schema(
        [
            (subject_id_field, subject_id_dtype),
            (time_field, time_dtype),  # Static events will have a null timestamp
            (code_field, code_dtype),
            (numeric_value_field, numeric_value_dtype),
        ]
        + custom_properties
    )
```

#### The label schema.
Models, when predicting this label, are allowed to use all data about a subject up to and including the
prediction time. Exclusive prediction times are not currently supported, but if you have a use case for them
please add a GitHub issue.

```python
label = pa.schema(
    [
        ("subject_id", pa.int64()),
        ("prediction_time", pa.timestamp("us")),
        ("boolean_value", pa.bool_()),
        ("integer_value", pa.int64()),
        ("float_value", pa.float64()),
        ("categorical_value", pa.string()),
    ]
)

Label = TypedDict("Label", {
    "subject_id": int,
    "prediction_time": datetime.datetime,
    "boolean_value": Optional[bool],
    "integer_value" : Optional[int],
    "float_value" : Optional[float],
    "categorical_value" : Optional[str],
}, total=False)
```

#### The subject split schema.

Three sentinel split names are defined for convenience and shared processing:
  1. A training split, named `train`, used for ML model training.
  2. A tuning split, named `tuning`, used for hyperparameter tuning. This is sometimes also called a
     "validation" split or a "dev" split. In many cases, standardizing on a tuning split is not necessary and
     models should feel free to merge this split with the training split if desired.
  3. A held-out split, named `held_out`, used for final model evaluation. In many cases, this is also called a
     "test" split. When performing benchmarking, this split should not be used at all for model selection,
     training, or for any purposes up to final validation.

Additional split names can be used by the user as desired.

```
train_split = "train"
tuning_split = "tuning"
held_out_split = "held_out"

subject_split = pa.schema(
    [
        ("subject_id", pa.int64()),
        ("split", pa.string()),
    ]
)
```

#### The dataset metadata schema.

```python
dataset_metadata = {
    "type": "object",
    "properties": {
        "dataset_name": {"type": "string"},
        "dataset_version": {"type": "string"},
        "etl_name": {"type": "string"},
        "etl_version": {"type": "string"},
        "meds_version": {"type": "string"},
        "created_at": {"type": "string"},  # Should be ISO 8601
    },
}

# Python type for the above schema

DatasetMetadata = TypedDict(
    "DatasetMetadata",
    {
        "dataset_name": NotRequired[str],
        "dataset_version": NotRequired[str],
        "etl_name": NotRequired[str],
        "etl_version": NotRequired[str],
        "meds_version": NotRequired[str],
        "created_at": NotRequired[str],  # Should be ISO 8601
    },
    total=False,
)
```

#### The code metadata schema.

```python
# Code metadata must contain at least one row for every unique code in the dataset
def code_metadata(custom_per_code_properties=[]):
    return pa.schema(
        [
            ("code", pa.string()),

            ("description", pa.string()),

            ("parent_codes", pa.list(pa.string()),
            # parent_codes must be a list of strings, each string being a higher level
            # code that represents a generalization of the provided code. Parent codes
            # can use any structure, but is recommended that they reference OMOP concepts
            # whenever possible, to enable use of more generic labeling functions and OHDSI tools.
            # OMOP concepts are referenced in these strings via the format "$VOCABULARY_NAME/$CONCEPT_NAME".
            # For example: "ICD9CM/487.0" would be a reference to ICD9 code 487.0
        ] + custom_per_code_properties
    )

# Python type for the above schema

CodeMetadata = TypedDict("CodeMetadata", {"code": str, "description": str, "parent_codes": List[str]}, total=False)
```
