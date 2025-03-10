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
    subject_id: pa.int64()
    time: pa.timestamp("us")  # noqa: F821 -- this seems to be a flake error
    code: pa.string()
    numeric_value: Optional(pa.float32()) = None


############################################################

# The label schema.


class Label(PyArrowSchema):
    allow_extra_columns: ClassVar[bool] = False

    subject_id: pa.int64()
    prediction_time: pa.timestamp("us")  # noqa: F821 -- this seems to be a flake error
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
    allow_extra_columns: ClassVar[bool] = False

    subject_id: pa.int64()
    split: pa.string()


############################################################

# The dataset metadata schema.
# This is a JSON schema.

dataset_metadata_filepath = os.path.join("metadata", "dataset.json")


class DatasetMetadata(JSONSchema):
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
    code: pa.string()
    description: pa.string()
    parent_codes: pa.list_(pa.string())
