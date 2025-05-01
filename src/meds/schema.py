"""The core schemas for the MEDS format.

Please see the README for more information, including expected file organization on disk, more details on what
each schema should capture, etc.
"""

import datetime
import os
from typing import ClassVar

import pyarrow as pa
from flexible_schema import JSONSchema, Optional, PyArrowSchema, Required

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


class DataSchema(PyArrowSchema):
    """The core data schema for MEDS. Stored in `$MEDS_ROOT/data/$SHARD_NAME.parquet`.

    This is a PyArrow schema that has
      - 3 mandatory columns (`subject_id`, `time`, `code`)
      - 2 optional columns (`numeric_value`, `text_value`)
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
        text_value: The text value for the event. A string. This is often used for both (a) measurements that
            have free-text descriptions, such as unstructured laboratory test results, and (b) free-text
            clinical notes.
    """

    subject_id: Required(pa.int64(), nullable=False)
    time: Required(pa.timestamp("us"), nullable=True)
    code: Required(pa.string(), nullable=False)
    numeric_value: Optional(pa.float32())
    text_value: Optional(pa.large_string())


############################################################

# The label schema.


class LabelSchema(PyArrowSchema):
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

    subject_id: Required(pa.int64(), nullable=False)
    prediction_time: Required(pa.timestamp("us"), nullable=False)
    boolean_value: Optional(pa.bool_(), nullable=False)
    integer_value: Optional(pa.int64(), nullable=False)
    float_value: Optional(pa.float32(), nullable=False)
    categorical_value: Optional(pa.string(), nullable=False)


############################################################

# The subject split schema.

subject_splits_filepath = os.path.join("metadata", "subject_splits.parquet")

train_split = "train"  # For ML training.
tuning_split = "tuning"  # For ML hyperparameter tuning. Also often called "validation" or "dev".
held_out_split = "held_out"  # For final ML evaluation. Also often called "test".


class SubjectSplitSchema(PyArrowSchema):
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

    subject_id: Required(pa.int64(), nullable=False)
    split: Required(pa.string(), nullable=False)


############################################################

# The dataset metadata schema.
# This is a JSON schema.

dataset_metadata_filepath = os.path.join("metadata", "dataset.json")


class DatasetMetadataSchema(JSONSchema):
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
        raw_source_id_columns: A list of columns in the data that are not part of the core MEDS data schema
            and contain identifiers or join keys to the raw source data. These will typically have no use
            outside of join operations in downstream modeling steps.
        code_modifier_columns: A list of columns in the data that are not part of the core MEDS data schema
            and contain "code modifiers" -- meaning columns that should be seen to "modify" the core code. For
            example, a code modifier might be a column that indicates the "unit" of a measurement, or a column
            that indicates the priority assigned to a laboratory test order. These columns are typically
            useful during subsequent pre-processing steps to enrich code group-by operations for aggregating
            over codes. These columns should all appear in the data schema and be strings.
        additional_value_modality_columns: A list of columns in the data that are not part of the core MEDS
            data schema but contain additional "value modalities" beyond numeric or text. These may include
            paths to imaging or waveform data, for example. Columns with consistent names that are used in
            this way will eventually be considered for promotion into the core MEDS schema.
        site_id_columns: A list of columns in the data that are not part of the core MEDS data schema and
            contain identifiers for the site of care.
        other_extension_columns: A list of columns in the data that are not part of the core MEDS data schema
            and contain other columns beyond those described above.
    """

    dataset_name: Optional(str)
    dataset_version: Optional(str)
    etl_name: Optional(str)
    etl_version: Optional(str)
    meds_version: Optional(str)
    created_at: Optional(datetime.datetime)
    license: Optional(str)
    location_uri: Optional(str)
    description_uri: Optional(str)
    raw_source_id_columns: Optional(list[str])
    code_modifier_columns: Optional(list[str])
    additional_value_modality_columns: Optional(list[str])
    site_id_columns: Optional(list[str])
    other_extension_columns: Optional(list[str])


############################################################

# The code metadata schema.
# This is a parquet schema.

code_metadata_filepath = os.path.join("metadata", "codes.parquet")


class CodeMetadataSchema(PyArrowSchema):
    """The schema for the code metadata file. Stored in `$MEDS_ROOT/metadata/codes.parquet`.

    This file contains additional details about the codes in the MEDS dataset. It is guaranteed that all
    unique codes in the dataset will be present in this file, for any valid MEDS dataset (though this property
    may or may not hold after pre-processing steps happen).

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

    code: Required(pa.string(), nullable=False)
    description: Optional(pa.string())
    parent_codes: Optional(pa.list_(pa.string()))
