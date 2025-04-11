<p align="center">
  <img width="200" height="200" src="https://medical-event-data-standard.github.io/img/logo.svg" alt="MEDS Logo">
</p>

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

## Table of Contents

- [Philosophy](#philosophy)
- [The Schemas](#the-schemas)
    - [The `Data` schema](#the-data-schema)
    - [The `DatasetMetadata` schema](#the-datasetmetadata-schema)
    - [The `CodeMetadata` schema](#the-codemetadata-schema)
    - [The `SubjectSplit` schema](#the-subjectsplit-schema)
    - [The `Label` schema](#the-label-schema)
- [Organization on Disk](#organization-on-disk)
    - [Organization of task labels](#organization-of-task-labels)
- [Validation](#validation)
- [Example: MIMIC-IV demo dataset](#example-mimic-iv-demo-dataset)

## Philosophy

At the heart of MEDS is a simple yet powerful idea: nearly all EHR data can be modeled as a minimal tuple. We believe that the essence of a clinical event can be effectively described using three core components:

1. _subject_: The primary entity for which care observations are recorded. Typically, this is an individual with a complete sequence of observations. In some datasets (e.g., eICU), a subject may refer to a single hospital admission rather than the entire individual record.

2. _time_: The time that the event was observed.

3. _code_: The descriptor of what event is being observed.

This minimalist representation captures the essence of EHR data while providing a consistent foundation for further analysis and enrichment.

## The Schemas

Building on this philosophy, MEDS defines five primary schema components:

| **Component**     | **Description**                                                                                                                       | **Implementation** |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `Data`            | Describes the core medical event data, organized as sequences of subject observations (i.e., events).                                 | PyArrow            |
| `DatasetMetadata` | Captures metadata about the source dataset, including its name, version, and details of its conversion to MEDS (e.g., ETL details).   | JSON               |
| `CodeMetadata`    | Provides metadata for the codes used to describe the types of measurements observed in the dataset.                                   | PyArrow            |
| `SubjectSplit`    | Stores information on how subjects are partitioned into subpopulations (e.g., training, tuning, held-out) for machine learning tasks. | PyArrow            |
| `Label`           | Defines the structure for labels that may be predicted about a subject at specific times in the subject record.                       | PyArrow            |

Below, each schema is introduced in detail. Usage examples and a practical demonstration with the [MIMIC-IV demo](https://physionet.org/content/mimic-iv-demo/2.2/) dataset are provided in a later section.

> [!IMPORTANT]
> Each component is implemented as a dataclass via the [`flexible_schema`](https://github.com/Medical-Event-Data-Standard/flexible_schema) package
> to provide convenient validation functionality. Under the hood, these are standard PyArrow schemas (for tabular data) or
> JSON schemas (for single-entity metadata).

### The `Data` schema

The `Data` schema describes a structure for the underlying medical data. It prescribes four fields that must appear in every MEDS data file:

1. `subject_id`: The ID of the subject this event is about.
2. `time`: The time of the event. This field is nullable for static events.
3. `code`: The code of the event.
4. `numeric_value`: The numeric value of the event. This field is nullable for non-numeric events.

Under the hood, this just defines a PyArrow schema, which can be accessed via the `.schema()` method:

```python
from meds import Data

Data.schema()
```

```console
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

There are a couple of recommended fields in this schema, all of which are optional:

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

```python
from meds import DatasetMetadata

DatasetMetadata.schema()
```

```console
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

This schema is intended to capture the context and provenance of the dataset.
A MEDS-compliant dataset should include this metadata to provide users with a clear understanding
of the data's origin and how it was transformed into the MEDS format. Note that since this
schema is about a single entity, it is the only one defined as a JSON schema.

### The `CodeMetadata` schema

The `CodeMetadata` schema provides additional details on how to describe the types of measurements (=codes) observed in the MEDS dataset.
It is designed to include metadata such as human-readable descriptions and ontological relationships for each code.

> [!NOTE]
> It is not guaranteed that all unique codes present in the dataset will be represented here—see [issue #57](https://github.com/Medical-Event-Data-Standard/meds/issues/57) for further discussion.

The core fields in this schema are:

1. `code`: A string representing the code for the event. This serves as the join key with the core MEDS data.
2. `description`: A human-readable description of the code.
3. `parent_codes`: A list of string identifiers for higher-level or parent codes in an ontological hierarchy. These may link to other codes in the file or external vocabularies (e.g., OMOP CDM).

```python
from meds import CodeMetadata

CodeMetadata.schema()
```

```console
code: string
description: string
parent_codes: list<item: string>
  child 0, item: string
```

As with the `Data` schema, the `CodeMetadata` schema can contain any number of custom columns to further describe the codes contained in the dataset.

### The `SubjectSplit` schema

The `SubjectSplit` schema defines how subjects were partitioned into groups for machine learning tasks. This schema consists of just two mandatory fields:

1. `subject_id`: The ID of the subject. This serves as the join key with the core MEDS data.
2. `split`: The name of the assigned split.

```python
from meds import SubjectSplit

SubjectSplit.schema()
```

```console
subject_id: int64
split: string
```

In line with common practice, MEDS also defines three sentinel split names for convenience and shared processing:

1. `train`: For model training.
2. `tuning`: For hyperparameter tuning (often referred to alternatively as the "validation" or "dev" set).
    In many cases, a tuning split may not be necessary and can be merged with the training set.
3. `held_out`: For final model evaluation (also commonly called the "test" set). When performing benchmarking,
    this split should **not** be used for any purpose except final model validation.

These sentinel names are available as exported variables:

```python
from meds import train_split, tuning_split, held_out_split

train_split, tuning_split, held_out_split
```

```console
('train', 'tuning', 'held_out')
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

Like the other schemas, this is implemented as a PyArrow schema but extra columns are *not* allowed.

```python
from meds import Label

Label.schema()
```

```console
subject_id: int64
prediction_time: timestamp[us]
boolean_value: bool
integer_value: int64
float_value: float
categorical_value: string
```

## Organization on Disk

A MEDS dataset is organized under a root directory (`$MEDS_ROOT`) into several subfolders corresponding to the different schema components. Below is an overview of the directory structure:

- **`$MEDS_ROOT/data/*`**

    - Contains the event data files following the `Data` schema.
    - Data is stored as a series of (possibly nested) sharded DataFrames in `parquet` format.
    - The file glob `glob("$MEDS_ROOT/data/**/*.parquet")` will match all these sharded files.
    - Each file holds all events for one or more subjects, each of which is sorted by time.

- **`$MEDS_ROOT/metadata/dataset.json`**

    - Contains metadata about the dataset and its production process, conforming to the `DatasetMetadata` schema.

- **`$MEDS_ROOT/metadata/codes.parquet`**

    - Holds per-code metadata as defined by the `CodeMetadata` schema.
    - This file lists metadata for every code observed in the full dataset and is not sharded.
    - (Some pre-processing may produce sharded code metadata files, but these reside in subdirectories under `$MEDS_ROOT/metadata/` and are not used for overall metadata operations.)

- **`$MEDS_ROOT/metadata/subject_splits.parquet`**

    - Contains information from the `SubjectSplit` schema, indicating how subjects are divided (e.g., training, tuning, held-out).

For ease of use, variables with the expected file paths are predefined:

```python
from meds import (
    data_subdirectory,
    dataset_metadata_filepath,
    code_metadata_filepath,
    subject_splits_filepath,
)

data_subdirectory, dataset_metadata_filepath, code_metadata_filepath, subject_splits_filepath
```

```console
('data', 'metadata/dataset.json', 'metadata/codes.parquet', 'metadata/subject_splits.parquet')
```

> [!IMPORTANT]
> MEDS data must satisfy two key properties:
>
> 1. **Subject Contiguity:** Data for a single subject must not be split across multiple parquet files.
> 2. **Sorted Order:** Data for a single subject must be contiguous within its file and sorted by time.

### Organization of task labels

Task label DataFrames are stored separately. Their location depends on two parameters:

- **`$TASK_ROOT`**: The root directory for task label data (often a subdirectory of `$MEDS_ROOT`, e.g., `$MEDS_ROOT/tasks`).
- **`$TASK_NAME`**: A parameter to separate different tasks (this value may include `/` characters, creating nested directories).

The file glob `glob($TASK_ROOT/$TASK_NAME/**/*.parquet)` is used to capture all task label files. Note that:

- The sharding of task label files may differ from that of the raw data files.
- In some cases, a shard may not contain any task labels if no subject qualifies for the task; such files might be empty or missing.

## Validation

The schema objects described above can be used to validate a dataset against the MEDS schema via the `.validate()` method. When you call this method, the input data is checked to ensure it contains all required columns with the correct types. If optional columns (such as `numeric_value` in the `Data` schema) are missing, they are automatically added with `null` values. This guarantees that the validated table conforms to the expected schema.

For example, consider the following code snippet that uses the `Data` schema to validate a made-up data file:

```python
import pyarrow as pa
import datetime
from meds import Data

data_tbl = pa.Table.from_pydict(
    {
        "code": ["A", "B", "C"],
        "subject_id": [1, 2, 3],
        "time": [
            datetime.datetime(2021, 3, 1),
            None,
            datetime.datetime(2021, 5, 1),
        ],
    }
)

Data.validate(data_tbl)
```

```console
pyarrow.Table
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float
----
subject_id: [[1,2,3]]
time: [[2021-03-01 00:00:00.000000,null,2021-05-01 00:00:00.000000]]
code: [["A","B","C"]]
numeric_value: [[null,null,null]]

```

In contrast, a DataFrame that does not conform to the schema will raise an error:

```python
invalid_tbl = data_tbl.select(["subject_id", "time"])
Data.validate(invalid_tbl)
```

```console
flexible_schema.base.SchemaValidationError: Missing mandatory columns: {'code'}
```

## Example: MIMIC-IV demo dataset

Let's look at the publicly available [MIMIC-IV demo](https://physionet.org/content/mimic-iv-demo/2.2/) dataset
for a concrete example of what a MEDS-compliant dataset may look like. We use [MIMIC_IV_MEDS](https://github.com/Medical-Event-Data-Standard/MIMIC_IV_MEDS) ETL pipeline to automatically download the MIMIC-IV demo dataset and convert it into MEDS format. After running the pipeline, we get a directory structure that looks like this:

```console
MEDS_cohort
├── ...
├── data
│   ├── held_out
│   │   └── 0.parquet
│   ├── train
│   │   └── 0.parquet
│   └── tuning
│       └── 0.parquet
├── ...
├── metadata
│   ├── codes.parquet
│   ├── dataset.json
│   └── subject_splits.parquet
└── ...
```

We can immediately see that the data is organized as described in the [Organization on Disk](#organization-on-disk) section, with the `data` directory containing the raw underlying event data and the `metadata` directory containing the metadata. The `data` directory contains three subdirectories, `train`, `tuning`, and `held_out`, corresponding to our default split names and each containing a data file in parquet format (since the MIMIC-IV demo dataset is small, we only have one data file per split but in general we would expect multiple shards).

Let's take a look at the contents of one of the data files in the `train` split, which looks something like this (note that we are using the polars package for better readability):

```python
from pyarrow import parquet as pq
import polars as pl

data_tbl = pq.read_table("data/train/0.parquet")
pl.from_arrow(data_tbl)
```

```console
shape: (803_992, 25)
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

For each entry, we have the `subject_id` of the person this observation is about, the `time` that the event was recorded, the `code` that describes what this information is about, and some optional fields (in this case `numeric_value`s and `text_value`s associated with the event).

```python
from meds import Data

Data.validate(data_tbl)
```

```console
pyarrow.Table
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float
text_value: large_string
...
----
subject_id: [[12345678,12345678,12345678,12345678,...]]
time: [[null,2138-01-01 00:00:00,2178-02-12 08:11:00,2178-02-12 11:38:00,...]]
code: [["GENDER//F","MEDS_BIRTH","LAB//51079//UNK","LAB//51237//UNK",...]]
numeric_value: [[null,null,null,1.4,...]]
text_value: [[null,null,"POS",null,...]]
...
```

The dataset metadata associated with this dataset is stored in the `metadata/dataset.json` file and looks like this:

```console
{
    "dataset_name": "MIMIC-IV",
    "dataset_version": "3.1:0.0.4",
    "etl_name": "MEDS_transforms",
    "etl_version": "0.2.2",
    "meds_version": "0.3.3",
    "created_at": "2025-03-28T13:47:38.809053"
}
```

The code metadata is stored in the `metadata/codes.parquet` file and looks like this:

```python
code_tbl = pq.read_table("metadata/codes.parquet")
pl.from_arrow(code_tbl)
```

```console
┌────────────────────────────┬──────────────────────────┬─────────────────────┬───────────┬─────┐
│ code                       ┆ description              ┆ parent_codes        ┆ itemid    ┆ ... │
│ ---                        ┆ ---                      ┆ ---                 ┆ ---       ┆ ... │
│ str                        ┆ str                      ┆ list[str]           ┆ list[str] ┆ ... │
╞════════════════════════════╪══════════════════════════╪═════════════════════╪═══════════╪═════╡
│ DIAGNOSIS//ICD//9//43820   ┆ Late effects of cerebro… ┆ ["ICD9CM/438.20"]   ┆ [null]    ┆ ... │
│ DIAGNOSIS//ICD//10//M25511 ┆ Pain in right shoulder   ┆ ["ICD10CM/M25.511"] ┆ [null]    ┆ ... │
│ LAB//51159//UNK            ┆ CD15 cells/100 cells in  ┆ ["LOINC/17117-3"]   ┆ ["51159"] ┆ ... │
│ LAB//51434//%              ┆ Other cells/100 leukocy… ┆ ["LOINC/76350-8"]   ┆ ["51434"] ┆ ... │
│ …                          ┆ …                        ┆ …                   ┆ …         ┆ ... │
└────────────────────────────┴──────────────────────────┴─────────────────────┴───────────┴─────┘
```

`itemid` is an example for an extension column that is not part of the core MEDS schema.
This is explicitly allowed for the code metadata file and validates accordingly:

```python
from meds import CodeMetadata

CodeMetadata.validate(code_tbl)
```

```console
pyarrow.Table
code: string
description: string
parent_codes: list<element: string>
  child 0, element: string
itemid: large_list<element: large_string>
  child 0, element: large_string
...
----
code: [["DIAGNOSIS//ICD//9//43820","DIAGNOSIS//ICD//10//M25511",...]]
description: [["Late effects of cerebrovascular disease","Pain in right shoulder",...]]
parent_codes: [[["ICD9CM/438.20"],["ICD10CM/M25.511"],...]]
itemid: [[[null],[null],...]]
...
```

Finally, we can look at the subject splits metadata to find out which subjects were assigned to which splits:

```python
split_tbl = pq.read_table("metadata/subject_splits.parquet")
pl.from_arrow(split_tbl)
```

```console
┌────────────┬──────────┐
│ subject_id ┆ split    │
│ ---        ┆ ---      │
│ i64        ┆ str      │
╞════════════╪══════════╡
│ 12345678   ┆ train    │
│ 12345679   ┆ train    │
│ 12345680   ┆ train    │
│ 12345681   ┆ train    │
│ 12345682   ┆ train    │
│ …          ┆ …        │
└────────────┴──────────┘
```

Note that label information is not included in the basic MIMIC-IV ETL, but you can find out more about how to create labels such as ICU mortality in the documentation of the [ACES package](https://eventstreamaces.readthedocs.io/en/latest/notebooks/examples.html).

## Springboard

Our website contains tutorials for getting started with MEDS and information about the current tools:

- [Converting to MEDS](https://medical-event-data-standard.github.io/docs/tutorial-basics/converting_to_MEDS)
- [Modeling over MEDS data](https://medical-event-data-standard.github.io/docs/tutorial-basics/modeling_over_MEDS_data)
- [Public Research Resources](https://medical-event-data-standard.github.io/docs/MEDS_datasets_and_models)
