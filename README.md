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

MEDS consists of five components/schemas:

1. A _data_ schema. This schema describes the underlying medical data, organized as sequences of subject
    observations.
2. A _dataset metadata_ schema. This schema contains metadata about the source dataset, such as its name and versions, and its conversion to MEDS, such as when it was transformed, using what version of what code, etc.
3. A _code metadata_ schema. This schema contains metadata describing the codes used to describe the
    types of measurements observed in the dataset.
4. A _subject split_ schema. This schema contains metadata about how subjects in the MEDS dataset are
    assigned to different subpopulations, most commonly used to dictate ML splits.
5. A _label_ schema. This schema describes labels that may be predicted about a subject
    at a given time in the subject record.

Below, each of these schemas are introduced in detail. Throughout this document, we will use the publicly available [MIMIC-IV demo dataset](https://physionet.org/content/mimic-iv-demo/2.2/) and [its conversion to MEDS](https://github.com/Medical-Event-Data-Standard/MIMIC_IV_MEDS) as a concrete example to see how these schemas might be used in practice.


### The data schema

The _data_ schema describes the underlying medical data and defines four fields that will appear in every MEDS data file:

1. `subject_id`: The ID of the subject this event is about.
2. `time`: The time of the event. This field is nullable for static events.
3. `code`: The code of the event.
4. `numeric_value`: The numeric value of the event. This field is nullable for non-numeric events.

In addition, it can contain any number of custom properties to further enrich observations. This is reflected
programmatically using the [`flexible_schema`](https://github.com/Medical-Event-Data-Standard/flexible_schema) package as the below schema:

```python
from flexible_schema import PyArrowSchema


class Data(PyArrowSchema):
    """The core data schema for MEDS. Stored in `$MEDS_ROOT/data/$SHARD_NAME.parquet`.

    This is a PyArrow schema that has
      - 3 mandatory columns (`subject_id`, `time`, `code`)
      - 1 optional column (`numeric_value`) (optional columns will be added with null values to tables)
      - Extra columns are allowed.

    Attributes:
        subject_id: The unique identifier for the subject. This is a 64-bit integer. Should not be null in the
            data.
        time: The time of the event. This is a timestamp with microsecond precision. May be null in the data
            for static measurements.
        code: The code for the event. This is a string (in an unspecified categorical vocabulary). Should not
            be null in the data.
        numeric_value: The numeric value for the event. A 32-bit float. May be null in the data for
            measurements lacking a numeric value. This column can be omitted wholesale from tables submitted
            for validation, and will be added to the returned, validated table with null values.
    """

    subject_id: pa.int64()
    time: pa.timestamp("us")  # noqa: F821 -- this seems to be a flake error
    code: pa.string()
    numeric_value: Optional(pa.float32()) = None
```

Under the hood, this just defines a PyArrow schema, which can be accessed via the `.schema()` method:

```python
>>> from meds import Data
>>> Data.schema()
subject_id: int64
time: timestamp[us]
code: string
numeric_value: float   
```


### The dataset metadata schema

The _dataset metadata_ schema documents important information about the underlying source dataset, including its name and version, 
as well as details about its conversion to MEDS, such as when it was transformed, using what version of what code, etc.


```python
class DatasetMetadata(JSONSchema):
    """The schema for the dataset metadata file. Stored in `$MEDS_ROOT/metadata/dataset.json`.

    This is a JSON schema that has only optional fields.

    Attributes:
        dataset_name: The name of the dataset.
        dataset_version: The version of the dataset.
        etl_name: The name of the ETL process that generated the dataset.
        etl_version: The version of the ETL process that generated the dataset.
        meds_version: The version of the MEDS format.
        created_at: The datetime the dataset was created. When serialized to JSON, is in ISO 8601 format.
        license: The license for the dataset.
        location_uri: The URI for the dataset location.
        description_uri: The URI for the dataset description.
        extension_columns: A list of columns in the data beyond those required in the core MEDS data schema.
    """

    dataset_name: Optional(str) = None
    dataset_version: Optional(str) = None
    etl_name: Optional(str) = None
    etl_version: Optional(str) = None
    meds_version: Optional(str) = None
    created_at: Optional(datetime.datetime) = None
    license: Optional(str) = None
    location_uri: Optional(str) = None
    description_uri: Optional(str) = None
    extension_columns: Optional(list[str]) = None
```

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



### The code metadata schema.

```python
class CodeMetadata(PyArrowSchema):
    """The schema for the code metadata file. Stored in `$MEDS_ROOT/metadata/codes.parquet`.

    This file contains additional details about the codes in the MEDS dataset. It is not guaranteed that all
    unique codes in the dataset will be present in this file. See
    https://github.com/Medical-Event-Data-Standard/meds/issues/57 if you would like to comment on this design
    or advocate for mandating that all codes be present in this file.

    This is a PyArrow schema that has
        - 3 mandatory columns (`code`, `description`, `parent_codes`)
        - Extra columns are allowed.

    As with all PyArrow schemas, these columns may be null in the data.

    Attributes:
        code: The code for the event. This is a string (in an unspecified categorical vocabulary). This is a
            join key with the core MEDS data.
        description: A human-readable description of the code.
        parent_codes: A list of string identifiers for "parents" of this code in an ontological sense. These
            codes may link to other codes in the `codes.parquet` file or to external vocabularies. Most
            typically, this is used to link to vocabularies in the OMOP CDM.
    """

    code: pa.string()
    description: pa.string()
    parent_codes: pa.list_(pa.string())
```

### The subject split schema.

As soon as we want to perform any ML on the data, there are usually a couple of additional steps we need to take. One of the most common ones is to split the data into training, tuning, and held-out sets. 

The _subject split_ schema is used to store these splits.
In line with common practice, three sentinel split names are defined for convenience and shared processing:

1. A training split, named `train`, used for ML model training.
2. A tuning split, named `tuning`, used for hyperparameter tuning. This is sometimes also called a
    "validation" split or a "dev" split. In many cases, standardizing on a tuning split is not necessary and
    models should feel free to merge this split with the training split if desired.
3. A held-out split, named `held_out`, used for final model evaluation. In many cases, this is also called a
    "test" split. When performing benchmarking, this split should not be used at all for model selection,
    training, or for any purposes up to final validation.

Additional split names can be used by the user as desired.

```python
train_split = "train"
tuning_split = "tuning"
held_out_split = "held_out"


class SubjectSplit(PyArrowSchema):
    """The schema for storing per-subject splits. Stored in `$MEDS_ROOT/metadata/subject_splits.parquet`.

    The subject splits are used to divide the subjects into training, tuning, and held-out sets at a
    per-subject level. Per-subject splits are currently the only supported split format in MEDS. Additional
    types of splits may be added in the future; see
    https://github.com/Medical-Event-Data-Standard/meds/issues/74 for more information and to contribute to
    the discussion on this point.

    We use the following default split names:
        - `train`: For training the model.
        - `tuning`: For hyperparameter tuning, early stopping, etc. This is also commonly called the
          "validation" or "dev" set.
        - `held_out`: For final evaluation of the model. This is also commonly called the "test" set.

    This is a PyArrow schema that has
        - 2 mandatory columns (`subject_id`, `split`)
        - Extra columns are not allowed.

    Attributes:
        subject_id: The unique identifier for the subject. This is a 64-bit integer. This field is a join key
            with the core MEDS data.
        split: The split for the subject. This is a string. Any value is permissible. The sentinel values of
            "train", "tuning", and "held_out" are recommended for training, tuning, and held-out sets.
    """

    allow_extra_columns: ClassVar[bool] = False

    subject_id: pa.int64()
    split: pa.string()
```



### The label schema.

Finally

Models, when predicting this label, are allowed to use all data about a subject up to and including the
prediction time. Exclusive prediction times are not currently supported, but if you have a use case for them
please add a GitHub issue.

```python
class Label(PyArrowSchema):
    """The label-file schema for MEDS. No dedicated storage path, but stored with parquet files.

    This schema may or may not be sharded, and may or may not reflect the same sharding as the core MEDS
    dataset.

    This is a PyArrow schema that has
      - 2 mandatory columns (`subject_id`, `prediction_time`)
      - 4 optional columns (`boolean_value`, `integer_value`, `float_value`, `categorical_value`). These
        represent the "labels" for the subject at the prediction time.
      - Extra columns are not allowed.

    Attributes:
        subject_id: The unique identifier for the subject. This is a 64-bit integer. This field is a join key
            with the core MEDS data.
        prediction_time: When predicting the given label for the subject, data may be used from this subject
            up to and including this time. This is a timestamp with microsecond precision.
        boolean_value: A boolean label for the subject at the prediction time. Used for binary classification.
        integer_value: An integer label for the subject at the prediction time. Used for multi-class
            classification or ordinal regression.
        float_value: A float label for the subject at the prediction time. Used for regression.
        categorical_value: A string label for the subject at the prediction time. Used for multi-class
            classification.
    """

    allow_extra_columns: ClassVar[bool] = False

    subject_id: pa.int64()
    prediction_time: pa.timestamp("us")  # noqa: F821 -- this seems to be a flake error
    boolean_value: Optional(pa.bool_()) = None
    integer_value: Optional(pa.int64()) = None
    float_value: Optional(pa.float32()) = None
    categorical_value: Optional(pa.string()) = None
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