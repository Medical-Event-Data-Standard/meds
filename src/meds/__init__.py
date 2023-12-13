import datetime
from typing import Any, List, Mapping

import pyarrow as pa
from typing_extensions import NotRequired, TypedDict

# Event Stream Data Standard consists of three main components:
# 1. A patient data schema
# 2. A label schema
# 3. A dataset metadata schema.
#
# Patient data and labels are specified using pyarrow. Dataset metadata is specified using JSON.

# We also provide TypedDict Python type signatures for these schemas.

############################################################

# The patient data schema.


def patient_schema(per_event_metadata_schema=pa.null()):
    # Return a patient schema with a particular per event metadata subschema
    measurement = pa.struct(
        [
            ("code", pa.string()),
            ("text_value", pa.string()),
            ("numeric_value", pa.float32()),
            ("datetime_value", pa.timestamp("us")),
            ("metadata", per_event_metadata_schema),
        ]
    )

    event = pa.struct([("time", pa.timestamp("us")), ("measurements", pa.list_(measurement))])

    patient = pa.schema(
        [
            ("patient_id", pa.int64()),
            ("events", pa.list_(event)),  # Require ordered by time
        ]
    )

    return patient


# Python types for the above schema

Measurement = TypedDict(
    "Measurement",
    {
        "code": str,
        "text_value": NotRequired[str],
        "numeric_value": NotRequired[float],
        "datetime_value": NotRequired[datetime.datetime],
        "metadata": NotRequired[Any],
    },
)

Event = TypedDict("Event", {"time": datetime.datetime, "measurements": List[Measurement]})

Patient = TypedDict("Patient", {"patient_id": int, "events": List[Event]})

############################################################

# The label schema.

label = pa.schema(
    [
        ("patient_id", pa.int64()),
        ("prediction_time", pa.timestamp("us")),
        ("boolean_value", pa.bool_()),
    ]
)

# Python types for the above schema

Label = TypedDict("Label", {"patient_id": int, "prediction_time": datetime.datetime, "boolean_value": bool})

############################################################

# The dataset metadata schema.

code_metadata_entry = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "parent_codes": {"type": "array", "items": {"type": "string"}},
    },
}

code_metadata = {
    "type": "object",
    "additionalProperties": code_metadata_entry,
}

dataset_metadata = {
    "type": "object",
    "properties": {
        "dataset_name": {"type": "string"},
        "dataset_version": {"type": "string"},
        "etl_name": {"type": "string"},
        "etl_version": {"type": "string"},
        "code_metadata": code_metadata,
    },
}

# Python types for the above schema

CodeMetadataEntry = TypedDict("CodeMetadataEntry", {"description": str, "standard_ontology_codes": List[str]})
CodeMetadata = Mapping[str, CodeMetadataEntry]
DatasetMetadata = TypedDict(
    "DatasetMetadata",
    {
        "dataset_name": NotRequired[str],
        "dataset_version": NotRequired[str],
        "etl_name": NotRequired[str],
        "etl_version": NotRequired[str],
        "code_metadata": NotRequired[CodeMetadata],
    },
)
