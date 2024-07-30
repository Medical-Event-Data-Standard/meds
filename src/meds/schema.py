import datetime
from typing import Any, List, Mapping, Optional

import pyarrow as pa
from typing_extensions import NotRequired, TypedDict

# Medical Event Data Standard consists of four main components:
# 1. A patient event schema
# 2. A label schema
# 3. A dataset metadata schema.
# 4. A code metadata schema.
#
# Event data, labels, and code metadata is specified using pyarrow. Dataset metadata is specified using JSON.

# We also specify a directory structure for how these should be laid out on disk.

# Every MEDS extract consists of a folder that contains both metadata and patient data with the following structure:
# - data/
#    A (possibly nested) folder containing multiple parquet files containing patient event data following the events_schema folder.
#    glob("data/**/*.parquet") is the recommended way for obtaining all patient event files.
# - dataset_metadata.json
#    Dataset level metadata containing information about the ETL used, data version, etc
# - (Optional) code_metadata.parquet
#    Code level metadata containing information about the code descriptions, standard mappings, etc
# - (Optional) patient_split.csv
#    A specification of patient splits that should be used.

############################################################

# The patient event data schema.
#
# Patient event data also must satisfy two important properties:
#
# 1. Patient event data cannot be split across parquet files. If a patient is in a dataset it must be in one and only one parquet file.
# 2. Patient event data must be contiguous within a particular parquet file and sorted by event time. 

# Both of these restrictions allow the stream rolling processing (see https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.rolling.html),
# which vastly simplifies many data analysis pipelines.

# We define some codes for particularly important events
birth_code = "MEDS_BIRTH"
death_code = "MEDS_DEATH"

def patient_events_schema(custom_per_event_properties=[]):
    return pa.schema(
        [
            ("patient_id", pa.int64()),
            ("time", pa.timestamp("us")), # Static events will have a null timestamp
            ("code", pa.string()),
            ("numeric_value", pa.float32()),
        ] + custom_per_event_properties
    )

# No python type is provided because Python tools for processing MEDS data will often provide their own types.
# See https://github.com/EthanSteinberg/meds_reader/blob/0.0.6/src/meds_reader/__init__.pyi#L55 for example.

############################################################

# The label schema.

label = pa.schema(
    [
        ("patient_id", pa.int64()),
        ("prediction_time", pa.timestamp("us")),
        ("boolean_value", pa.bool_()),
        ("integer_value", pa.int64()),
        ("float_value", pa.float64()),
        ("categorical_value", pa.string()),
    ]
)

# Python types for the above schema

Label = TypedDict("Label", {
    "patient_id": int, 
    "prediction_time": datetime.datetime, 
    "boolean_value": Optional[bool],
    "integer_value" : Optional[int],
    "float_value" : Optional[float],
    "categorical_value" : Optional[str],
}, total=False)


############################################################

# The patient split schema.

train_split = "train"
tuning_split = "tuning"
test_split = "test"

patient_split = pa.schema(
    [
        ("patient_id", pa.int64()),
        ("split", pa.string()),
    ]
)

PatientSplit = TypedDict("PatientSplit", {
    "patient_id": int,
    "split": str,
}, total=True)

############################################################

# The dataset metadata schema.
# This is a JSON schema.
# This data should be stored in dataset_metadata.json within the dataset folder.


dataset_metadata = {
    "type": "object",
    "properties": {
        "dataset_name": {"type": "string"},
        "dataset_version": {"type": "string"},
        "etl_name": {"type": "string"},
        "etl_version": {"type": "string"},
        "meds_version": {"type": "string"},
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
    },
    total=False,
)

############################################################

# The code metadata schema.
# This is a parquet schema.
# This data should be stored in code_metadata.parquet within the dataset folder.

def code_metadata_schema(custom_per_code_properties=[]): 
    code_metadata = pa.schema(
        [
            ("code", pa.string()),
            ("description", pa.string()),
            ("parent_codes", pa.list(pa.string()),
        ] + custom_per_code_properties
    )

    return code_metadata

# Python type for the above schema

CodeMetadata = TypedDict("CodeMetadata", {"code": str, "description": str, "parent_codes": List[str]}, total=False)
