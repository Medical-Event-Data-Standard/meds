import datetime

import jsonschema
import pyarrow as pa
import pytest

from meds import (
    data_schema, label_schema, dataset_metadata_schema, patient_split_schema, code_metadata_schema,
    train_split, tuning_split, held_out_split
)

def test_data_schema():
    """
    Test that mock data follows the data schema.
    """
    # Each element in the list is a row in the table
    raw_data = [
        {
            "patient_id": 123,
            "time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "code": "some_code",
            "text_value": "Example",
            "numeric_value": 10.0,
        }
    ]

    schema = data_schema([("text_value", pa.string())])

    table = pa.Table.from_pylist(raw_data, schema=schema)
    assert table.schema.equals(schema), "Patient schema does not match"

def test_code_metadata_schema():
    """
    Test that mock code metadata follows the schema.
    """
    # Each element in the list is a row in the table
    code_metadata = [
        {
            "code": "some_code",
            "description": "foo",
            "parent_code": ["parent_code"],
        }
    ]

    schema = code_metadata_schema()

    table = pa.Table.from_pylist(code_metadata, schema=schema)
    assert table.schema.equals(schema), "Code metadata schema does not match"

def test_patient_split_schema():
    """
    Test that mock data follows the data schema.
    """
    # Each element in the list is a row in the table
    patient_split_data = [
        {"patient_id": 123, "split": train_split},
        {"patient_id": 123, "split": tuning_split},
        {"patient_id": 123, "split": held_out_split},
        {"patient_id": 123, "split": "special"},
    ]

    table = pa.Table.from_pylist(patient_split_data, schema=patient_split_schema)
    assert table.schema.equals(patient_split_schema), "Patient split schema does not match"

def test_label_schema():
    """
    Test that mock label data follows the label schema.
    """
    # Each element in the list is a row in the table
    label_data = [
        {
            "patient_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "boolean_value": True
        }
    ]
    label_table = pa.Table.from_pylist(label_data, schema=label_schema)
    assert label_table.schema.equals(label_schema), "Label schema does not match"

    label_data = [
        {
            "patient_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "integer_value": 4
        }
    ]
    label_table = pa.Table.from_pylist(label_data, schema=label_schema)
    assert label_table.schema.equals(label_schema), "Label schema does not match"
    
    label_data = [
        {
            "patient_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "float_value": 0.4
        }
    ]
    label_table = pa.Table.from_pylist(label_data, schema=label_schema)
    assert label_table.schema.equals(label_schema), "Label schema does not match"
    
    label_data = [
        {
            "patient_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "categorical_value": "text"
        }
    ]
    label_table = pa.Table.from_pylist(label_data, schema=label_schema)
    assert label_table.schema.equals(label_schema), "Label schema does not match"

def test_dataset_metadata_schema():
    """
    Test that mock metadata follows dataset_metadata schema.
    """
    metadata = {
        "dataset_name": "Test Dataset",
        "dataset_version": "1.0",
        "etl_name": "Test ETL",
        "etl_version": "1.0",
    }

    jsonschema.validate(instance=metadata, schema=dataset_metadata_schema)
    assert True, "Dataset metadata schema validation failed"
