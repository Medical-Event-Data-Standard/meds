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

## Philosophy

At the heart of MEDS is a simple yet powerful idea: nearly all EHR data can be modeled as a minimal tuple. We believe that the essence of a clinical event can be effectively described using three core components: 

1. _subject_: The primary entity for which care observations are recorded. Typically, this is an individual with a complete sequence of observations. In some datasets (e.g., eICU), a subject may refer to a single hospital admission rather than the entire individual record.

2. _time_: The time that the event was observed.

3. _code_: The descriptor of what event is being observed.

This minimalist representation captures the essence of EHR data while providing a consistent foundation for further analysis and enrichment.



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


`DatasetMetadata` is defined as a JSON schema, which can again be accessed via the `.schema()` method:

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

The `SubjectSplit` schema defines how subjects were partitioned into groups for machine learning tasks. This schema consists of two mandatory fields:

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

In line with common practice, MEDS defines three sentinel split names for convenience and shared processing:

1. `train`: For model training.
2. `tuning`: For hyperparameter tuning (often referred to alternatively as the "validation" or "dev" set). 
    In many cases, a tuning split may not be necessary and can be merged with the training set.
3. `held_out`: For final model evaluation (also commonly called the "test" set). When performing benchmarking, 
    this split should **not** be used for any purpose except final model validation.

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

Like the other schemas, this is implemented as a PyArrow schema, and extra columns are not allowed.

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


For ease of use, variables the expected file paths are predefined:

```python
from meds.schema import (
    data_subdirectory,
    dataset_metadata_filepath,
    code_metadata_filepath,
    subject_splits_filepath
)
data_subdirectory, dataset_metadata_filepath, code_metadata_filepath, subject_splits_filepath
```
```console
('data', 'metadata/dataset.json', 'metadata/codes.parquet', 'metadata/subject_splits.parquet')
```

> **Important:** MEDS data must satisfy two key properties:
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