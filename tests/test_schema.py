import datetime

import jsonschema
import pyarrow as pa

from meds import (
    CodeMetadata,
    Data,
    DatasetMetadata,
    Label,
    SubjectSplit,
    held_out_split,
    train_split,
    tuning_split,
)


def test_consistency():
    assert Data.code_name == CodeMetadata.code_name
    assert Data.code_dtype == CodeMetadata.code_dtype
    assert Data.subject_id_name == SubjectSplit.subject_id_name
    assert Data.subject_id_dtype == SubjectSplit.subject_id_dtype
    assert Data.subject_id_name == Label.subject_id_name
    assert Data.subject_id_dtype == Label.subject_id_dtype
    assert Data.time_dtype == Label.prediction_time_dtype


def test_data_schema():
    """Test that mock data follows the data schema."""
    # Each element in the list is a row in the table
    raw_data = [
        {
            "subject_id": 123,
            "time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "code": "some_code",
            "text_value": "Example",
            "numeric_value": 10.0,
        }
    ]

    Data.validate(pa.Table.from_pylist(raw_data))


def test_code_metadata_schema():
    """Test that mock code metadata follows the schema."""
    # Each element in the list is a row in the table
    code_metadata = [
        {
            "code": "some_code",
            "description": "foo",
            "parent_codes": ["parent_codes"],
        }
    ]

    CodeMetadata.validate(pa.Table.from_pylist(code_metadata))


def test_subject_splits_schema():
    """Test that mock data follows the data schema."""
    # Each element in the list is a row in the table
    subject_splits_data = [
        {"subject_id": 123, "split": train_split},
        {"subject_id": 123, "split": tuning_split},
        {"subject_id": 123, "split": held_out_split},
        {"subject_id": 123, "split": "special"},
    ]

    SubjectSplit.validate(pa.Table.from_pylist(subject_splits_data))


def test_label_schema():
    """Test that mock label data follows the label schema."""
    # Each element in the list is a row in the table
    label_data = [
        {
            "subject_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "boolean_value": True,
        }
    ]
    Label.validate(pa.Table.from_pylist(label_data))

    label_data = [
        {
            "subject_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "integer_value": 4,
        }
    ]
    Label.validate(pa.Table.from_pylist(label_data))

    label_data = [
        {
            "subject_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "float_value": 0.4,
        }
    ]
    Label.validate(pa.Table.from_pylist(label_data))

    label_data = [
        {
            "subject_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "float_value": 0.4,
        }
    ]
    Label.validate(pa.Table.from_pylist(label_data))

    label_data = [
        {
            "subject_id": 123,
            "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "categorical_value": "text",
        }
    ]
    Label.validate(pa.Table.from_pylist(label_data))


def test_dataset_metadata_schema():
    """Test that mock metadata follows dataset_metadata schema."""
    metadata = {
        "dataset_name": "Test Dataset",
        "dataset_version": "1.0",
        "etl_name": "Test ETL",
        "etl_version": "1.0",
    }

    try:
        jsonschema.validate(instance=metadata, schema=DatasetMetadata.schema())

        dataset_metadata = DatasetMetadata(**metadata)
        jsonschema.validate(instance=dataset_metadata.to_dict(), schema=DatasetMetadata.schema())
    except Exception as e:
        raise AssertionError(f"Dataset metadata does not follow schema: {e}") from e
