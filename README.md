# Medical Event Data Standard

[![PyPI - Version](https://img.shields.io/pypi/v/meds)](https://pypi.org/project/meds/)
![python](https://img.shields.io/badge/-Python_3.10-blue?logo=python&logoColor=white)
[![codecov](https://codecov.io/gh/Medical-Event-Data-Standard/meds/graph/badge.svg?token=89SKXPKVRA)](https://codecov.io/gh/Medical-Event-Data-Standard/meds)
[![tests](https://github.com/Medical-Event-Data-Standard/meds/actions/workflows/tests.yaml/badge.svg)](https://github.com/Medical-Event-Data-Standard/meds/actions/workflows/tests.yml)
[![code-quality](https://github.com/Medical-Event-Data-Standard/meds/actions/workflows/code-quality-main.yaml/badge.svg)](https://github.com/Medical-Event-Data-Standard/meds/actions/workflows/code-quality-main.yaml)
[![license](https://img.shields.io/badge/License-MIT-green.svg?labelColor=gray)](https://github.com/Medical-Event-Data-Standard/meds#license)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Medical-Event-Data-Standard/meds/pulls)
[![contributors](https://img.shields.io/github/contributors/Medical-Event-Data-Standard/meds.svg)](https://github.com/Medical-Event-Data-Standard/meds/graphs/contributors)

![The MEDS data schema](static/data_figure.svg)

The Medical Event Data Standard (MEDS) is a data schema for storing streams of medical events, often
sourced from either Electronic Health Records or claims records. For more information, tutorials, and
compatible tools see the website: https://medical-event-data-standard.github.io/.

## Terminology

Before we define the various schemas that make up MEDS, we will define some key terminology that we use in this standard: 

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

## The Schemas

MEDS is composed of five primary schema components:

| **Component**         | **Description**                                                                                                                                                           | **Implementation** |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `Data`              | Describes the core medical event data, organized as sequences of subject observations (i.e., events).                                                                       | PyArrow schema                |
| `DatasetMetadata`  | Captures metadata about the source dataset, including its name, version, and details of its conversion to MEDS (e.g., ETL details).               | JSON schema                   |
| `CodeMetadata`     | Provides metadata for the codes used to describe the types of measurements observed in the dataset.                                                                       | PyArrow schema                |
| `SubjectSplit`     | Stores information on how subjects are partitioned into subpopulations (e.g., training, tuning, held-out) for machine learning tasks.                                    | PyArrow schema                |
| `Label`             | Defines the structure for labels that may be predicted about a subject at specific times in the subject record.                                                           | PyArrow schema                |

> [!Important]
> Each component is implemented as a dataclass via the [`flexible_schema` package](https://github.com/Medical-Event-Data-Standard/flexible_schema) 
> to provide convenient validation functionality. Under the hood, these are standard PyArrow schemas (for tabular data) or 
> JSON schemas (for single-entity metadata).


Below, each schema is introduced in detail. Usage examples and a practical demonstration with the [MIMIC-IV demo dataset](https://physionet.org/content/mimic-iv-demo/2.2/) dataset are provided in a later section.


### The `Data` schema

The `Data` schema describes a structure for the underlying medical data. It prescribes four fields that must appear in every MEDS data file:

1. `subject_id`: The ID of the subject this event is about.
2. `time`: The time of the event. This field is nullable for static events.
3. `code`: The code of the event.
4. `numeric_value`: The numeric value of the event. This field is nullable for non-numeric events.

Under the hood, this just defines a PyArrow schema, which can be accessed via the `.schema()` method:

```python
>>> from meds import Data
>>> Data.schema()
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float   
```

In addition, a MEDS-compliant data file can contain any number of custom columns to further enrich observations. 
Examples of such columns include further ID columns such as `hadm_id` or `icustay_id` to uniquely identify events, 
additional value types such as `text_value`, or additional metadata such as `ordercategorydescription`.



### The `DatasetMetadata` schema

The `DatasetMetadata` schema structures essential information about the source dataset and its conversion to MEDS. 
It includes details such as the dataset’s name, version, and licensing, as well as specifics about the ETL process 
used for transformation.

The key fields defined in this schema are:

1. `dataset_name`: The name of the dataset.
2. `dataset_version`: The version of the dataset.
3. `etl_name`: The name of the ETL process that generated the MEDS dataset.
4. `etl_version`: The version of the ETL process.
5. `meds_version`: The version of the MEDS format used.
6. `created_at`: The creation date and time (in ISO 8601 format).
7. `license`: The license under which the dataset is released.
8. `location_uri`: The URI where the dataset is hosted.
9. `description_uri`: The URI containing a detailed description of the dataset.
10. `extension_columns`: A list of additional columns present in the dataset beyond the core MEDS schema.


Under the hood, this just defines a JSON schema, which can again be accessed via the `.schema()` method:

```python
>>> from meds import DatasetMetadata
>>> DatasetMetadata.schema()
{
    'type': 'object', 
    'properties': {
        'dataset_name': {'type': 'string'}, 
        'dataset_version': {'type': 'string'}, 
        'etl_name': {'type': 'string'}, 
        'etl_version': {'type': 'string'}, 
        'meds_version': {'type': 'string'}, 
        'created_at': {'type': 'string', 'format': 'date-time'}, 
        'license': {'type': 'string'}, 
        'location_uri': {'type': 'string'}, 
        'description_uri': {'type': 'string'}, 
        'extension_columns': {'type': 'array', 'items': {'type': 'string'}}
    }, 
    'required': [], 
    'additionalProperties': True
}
```

This schema is intended to capture the complete context and provenance of the dataset. 
A MEDS-compliant dataset should include this metadata to provide users with a clear understanding 
of the data's origin and how it was transformed into the MEDS format.


### The `CodeMetadata` schema

The `CodeMetadata` schema provides additional details on how to describe the types of measurements (=codes) observed in the MEDS dataset. 
It is designed to include metadata such as human-readable descriptions and ontological relationships for each code. Note that it is not guaranteed that all unique codes present in the dataset will be represented here—see [issue #57](https://github.com/Medical-Event-Data-Standard/meds/issues/57) for further discussion.

The core fields in this schema are:

1. `code`: A string representing the code for the event. This serves as the join key with the core MEDS data.
2. `description`: A human-readable description of the code.
3. `parent_codes`: A list of string identifiers for higher-level or parent codes in an ontological hierarchy. These may link to other codes in the file or external vocabularies (e.g., OMOP CDM).

```python
>>> from meds import CodeMetadata
>>> CodeMetadata.schema()
code: string
description: string
parent_codes: list<item: string>
  child 0, item: string
```

As with the `Data` schema, the `CodeMetadata` schema can contain any number of custom columns to further describe the codes contained in the dataset.


### The `SubjectSplit` schema

The `SubjectSplit` schema defines how subjects were partitioned into groups for machine learning tasks. This schema consists of two mandatory fields:

1. `subject_id`: The ID of the subject. This serves as the join key with the core MEDS data.
2. `split`: The name of the assigned split.


```python
>>> from meds import SubjectSplit
>>> SubjectSplit.schema()
subject_id: int64
split: string
```

In line with common practice, MEDS defines three sentinel split names for convenience and shared processing:

1. `train`: For model training.
2. `tuning`: For hyperparameter tuning (often referred to alternatively as the "validation" or "dev" set). 
    In many cases, a tuning split may not be necessary and can be merged with the training set.
3. `held_out`: For final model evaluation (also commonly called the "test" set). When performing benchmarking, 
    this split should **not** be used for any purpose except final model validation.

```python
>>> from meds import train_split, tuning_split, held_out_split
>>> train_split
'train'
>>> tuning_split 
'tuning'
>>> held_out_split 
'held_out'
```

### The `Label` schema

The `Label` schema specifies the structure for labels that may be predicted about a subject at a given time. Models can use all data for a subject up to and including the prediction time (exclusive prediction times are not supported; please open a GitHub issue if needed).

The key fields in the Label schema are:
1. `subject_id`: The ID of the subject. This serves as the join key with the core MEDS data.
2. `prediction_time`: The time of the prediction. This field is nullable for static labels.
3. `boolean_value`: The boolean value of the label. This field is nullable for non-boolean labels.
4. `integer_value`: The integer value of the label. This field is nullable for non-integer labels.
5. `float_value`: The float value of the label. This field is nullable for non-float labels.
6. `categorical_value`: The categorical value of the label. This field is nullable for non-categorical labels.

Like the other schemas, this is implemented as a PyArrow schema, and extra columns are not allowed.

```python
>>> from meds import Label
>>> Label.schema()
subject_id: int64
prediction_time: timestamp[us]
boolean_value: bool
integer_value: int64
float_value: float
categorical_value: string
```


## Organization on Disk

Given a MEDS dataset stored in the `$MEDS_ROOT` directory data of the various schemas outlined above can be
found in the following subfolders:

- `$MEDS_ROOT/data/`: This directory will contain data in the _data_ schema, organized as a
    series of possibly nested sharded dataframes stored in `parquet` files. In particular, the file glob
    `glob("$MEDS_ROOT/data/**/*.parquet)` will capture all sharded data files of the raw MEDS data, all
    organized into _data schema_ files, sharded by subject and sorted, for each subject, by
    time.
- `$MEDS_ROOT/metadata/dataset.json`: This schema contains metadata in the _dataset metadata_ schema about
    the dataset and its production process.
- `$MEDS_ROOT/metadata/codes.parquet`: This file contains per-code metadata in the _code metadata_ schema
    about the MEDS dataset. All codes within the dataset should have an entry in this file.
    As this dataset describes all codes observed in the full MEDS dataset, it is _not_
    sharded. Note that some pre-processing operations may, at times, produce sharded code metadata files, but
    these will always appear in subdirectories of `$MEDS_ROOT/metadata/` rather than at the top level, and
    should generally not be used for overall metadata operations.
- `$MEDS_ROOT/metadata/subject_splits.parquet`: This schema contains information in the _subject split
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

> [!Important]
> MEDS data must further satisfy two important properties: 
>
> 1. Data about a single subject cannot be split across parquet files. If a subject is in a dataset it must be
>    in one and only one parquet file. 
> 2. Data about a single subject must be contiguous within a particular parquet file and sorted by time. 




## Validation

This schema can be used to generate the mandatory schema elements and/or validate or enforce a compliant MEDS
schema via the `.validate()` method:

```python
>>> import pyarrow as pa
>>> import datetime
>>> from meds import Data
>>> Data.schema()
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float
>>> data_tbl = pa.Table.from_pydict({
...     "code": ["A", "B", "C"],
...     "subject_id": [1, 2, 3],
...     "time": [
...         datetime.datetime(2021, 3, 1),
...         datetime.datetime(2021, 4, 1),
...         datetime.datetime(2021, 5, 1),
...     ],
... })
>>> Data.validate(data_tbl)
pyarrow.Table
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float
----
subject_id: [[1,2,3]]
time: [[2021-03-01 00:00:00.000000,2021-04-01 00:00:00.000000,2021-05-01 00:00:00.000000]]
code: [["A","B","C"]]
numeric_value: [[null,null,null]]

```



This can be used to generate a JSON schema for the dataset metadata via the `.to_json_schema()` method:

```python
>>> from meds import DatasetMetadata
>>> DatasetMetadata.schema() # doctest: +NORMALIZE_WHITESPACE
{'type': 'object',
 'properties': {'dataset_name': {'type': 'string'},
                'dataset_version': {'type': 'string'},
                'etl_name': {'type': 'string'},
                'etl_version': {'type': 'string'},
                'meds_version': {'type': 'string'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'license': {'type': 'string'},
                'location_uri': {'type': 'string'},
                'description_uri': {'type': 'string'},
                'extension_columns': {'type': 'array', 'items': {'type': 'string'}}},
 'required': [],
 'additionalProperties': True}

```


Let's look at the publicly available MIMIC-IV demo dataset for a concrete example of what a MEDS data file may look like.

```python
┌────────────┬─────────────────────┬──────────────────────┬───────────────┬────────────┬───┐
│ subject_id ┆ time                ┆ code                 ┆ numeric_value ┆ text_value ┆ … │
│ ---        ┆ ---                 ┆ ---                  ┆ ---           ┆ ---        ┆   │
│ i64        ┆ datetime[μs]        ┆ str                  ┆ f32           ┆ str        ┆   │
╞════════════╪═════════════════════╪══════════════════════╪═══════════════╪════════════╪═══╡
│ 12345678   ┆ null                ┆ GENDER//M            ┆ null          ┆ null       ┆ … │
│ 12345678   ┆ 2138-01-01 00:00:00 ┆ MEDS_BIRTH           ┆ null          ┆ null       ┆ … │
│ 12345678   ┆ 2178-02-12 08:11:00 ┆ LAB//51079//UNK      ┆ null          ┆ POS        ┆ … │
│ 12345678   ┆ 2178-02-12 11:38:00 ┆ LAB//51237//UNK      ┆ 1.4           ┆ null       ┆ … │
│ …          ┆ …                   ┆ …                    ┆ …             ┆ …          ┆ … │
└────────────┴─────────────────────┴──────────────────────┴───────────────┴────────────┴───┘
```

For each entry, we have the `subject_id` of the person this observation is about, the `time` that the event was recorded, the `code` that describes what this information is about, and some optional fields for the `numeric_value` and/or `text_value` associated with the event.


A MEDS-compliant example for MIMIC-IV would be:

```python
DatasetMetadata = {
    "dataset_name": "MIMIC-IV",
    "dataset_version": "3.1",
    "etl_name": "MIMIC-IV ETL",
    "etl_version": "0.0.3",
    "meds_version": "0.3.3",
    "created_at": "2025-01-01T00:00:00",
    "license": "PhysioNet Credentialed Health Data License 1.5.0",
    "location_uri": "https://physionet.org/content/mimiciv/",
    "description_uri": "https://mimic.mit.edu/docs/iv/",
    "extension_columns": [
        "insurance",
        "language",
        "marital_status",
        "race",
        "hadm_id",
        "drg_severity",
        "drg_mortality",
        "emar_id",
        "emar_seq",
        "priority",
        "route",
        "frequency",
        "doses_per_24_hrs",
        "poe_id",
        "icustay_id",
        "order_id",
        "link_order_id",
        "unit",
        "ordercategorydescription",
        "statusdescription",
    ],
}
```