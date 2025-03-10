"""The core schemas for the MEDS format.

Please see the README for more information, including expected file organization on disk, more details on what
each schema should capture, etc.
"""
import datetime
import os
from typing import ClassVar

from flexible_schema import JSONSchema, PyArrowSchema

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
    subject_id: int
    time: datetime.datetime
    code: str
    numeric_value: str | None = None


############################################################

# The label schema.


class Label(PyArrowSchema):
    allow_extra_columns: ClassVar[bool] = False
    subject_id: int
    prediction_time: datetime.datetime
    boolean_value: bool | None = None
    integer_value: int | None = None
    float_value: float | None = None
    categorical_value: str | None = None


############################################################

# The subject split schema.

subject_splits_filepath = os.path.join("metadata", "subject_splits.parquet")

train_split = "train"  # For ML training.
tuning_split = "tuning"  # For ML hyperparameter tuning. Also often called "validation" or "dev".
held_out_split = "held_out"  # For final ML evaluation. Also often called "test".


class SubjectSplit(PyArrowSchema):
    allow_extra_columns: ClassVar[bool] = False
    subject_id: int
    split: str


############################################################

# The dataset metadata schema.
# This is a JSON schema.

dataset_metadata_filepath = os.path.join("metadata", "dataset.json")


class DatasetMetadata(JSONSchema):
    dataset_name: str | None = None
    dataset_version: str | None = None
    etl_name: str | None = None
    etl_version: str | None = None
    meds_version: str | None = None
    created_at: datetime.datetime | None = None
    license: str | None = None
    location_uri: str | None = None
    description_uri: str | None = None
    extension_columns: list[str] | None = None


############################################################

# The code metadata schema.
# This is a parquet schema.

code_metadata_filepath = os.path.join("metadata", "codes.parquet")


class CodeMetadata(PyArrowSchema):
    code: str
    description: str
    parent_codes: list[str]
