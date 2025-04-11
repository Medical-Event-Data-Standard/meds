"""The core schemas for the MEDS format.

Please see the README for more information, including expected file organization on disk, more details on what
each schema should capture, etc.
"""

import datetime
import os
from typing import ClassVar

import pyarrow as pa
from flexible_schema import JSONSchema, Optional, PyArrowSchema

############################################################

# The data schema.
#
# MEDS data also must satisfy two important properties:
#
# 1. Data about a single subject cannot be split across parquet files.
#   If a subject is in a dataset it must be in one and only one parquet file.
# 2. Data about a single subject must be contiguous within a particular parquet file and sorted by time.

# Both of these restrictions allow the stream rolling processing (see https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.rolling.html), # noqa: E501
# which vastly simplifies many data analysis pipelines.

data_subdirectory = "data"

# We define some codes for particularly important events
birth_code = "MEDS_BIRTH"
death_code = "MEDS_DEATH"


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
    time: pa.timestamp("us")
    code: pa.string()
    numeric_value: Optional(pa.float32()) = None


############################################################

# The label schema.


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
    prediction_time: pa.timestamp("us")
    boolean_value: Optional(pa.bool_()) = None
    integer_value: Optional(pa.int64()) = None
    float_value: Optional(pa.float32()) = None
    categorical_value: Optional(pa.string()) = None


############################################################

# The subject split schema.

subject_splits_filepath = os.path.join("metadata", "subject_splits.parquet")

train_split = "train"  # For ML training.
tuning_split = "tuning"  # For ML hyperparameter tuning. Also often called "validation" or "dev".
held_out_split = "held_out"  # For final ML evaluation. Also often called "test".


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
            "train", "tuning", and "held_out" are recommended for training, tuning, and held-out sets,
    """

    allow_extra_columns: ClassVar[bool] = False

    subject_id: pa.int64()
    split: pa.string()


############################################################

# The dataset metadata schema.
# This is a JSON schema.

dataset_metadata_filepath = os.path.join("metadata", "dataset.json")


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


############################################################

# The code metadata schema.
# This is a parquet schema.

code_metadata_filepath = os.path.join("metadata", "codes.parquet")


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
