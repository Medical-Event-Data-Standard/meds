import datetime

import jsonschema
import pyarrow as pa
import pytest

from meds import patient_schema, label, dataset_metadata


def test_patient_schema():
    """
    Test that mock patient data follows the patient_schema schema.
    """
    patient_data = {
        "patient_id": [123],
        "events": [[{  # Nested list for events
            "time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "measurements": [{  # Nested list for measurements
                "code": "some_code",
                "text_value": "Example",
                "numeric_value": 10.0,
                "datetime_value": datetime.datetime(2020, 1, 1, 12, 0, 0),
                "metadata": None
            }]
        }]]
    }

    patient_table = pa.Table.from_pydict(patient_data, schema=patient_schema())
    assert patient_table.schema.equals(patient_schema()), "Patient schema does not match"

def test_label_schema():
    """
    Test that mock label data follows the label schema.
    """
    label_data = {
        "patient_id": [123],
        "prediction_time": [datetime.datetime(2020, 1, 1, 12, 0, 0)],
        "boolean_value": [True]
    }

    label_table = pa.Table.from_pydict(label_data, schema=label)
    assert label_table.schema.equals(label), "Label schema does not match"

def test_dataset_metadata_schema():
    """
    Test that mock metadata follows dataset_metadata schema.
    """
    metadata = {
        "dataset_name": "Test Dataset",
        "dataset_version": "1.0",
        "etl_name": "Test ETL",
        "etl_version": "1.0",
        "code_metadata": {
            "test_code": {
                "description": "A test code",
                "standard_ontology_codes": ["12345"],
            }
        },
    }

    jsonschema.validate(instance=metadata, schema=dataset_metadata)
    assert True, "Dataset metadata schema validation failed"
