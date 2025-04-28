import datetime

import jsonschema
import pyarrow as pa

from meds import (
    CodeMetadataSchema,
    DataSchema,
    DatasetMetadataSchema,
    LabelSchema,
    SubjectSplitSchema,
    held_out_split,
    train_split,
    tuning_split,
)


def test_consistency():
    assert DataSchema.code_name == CodeMetadataSchema.code_name
    assert DataSchema.code_dtype == CodeMetadataSchema.code_dtype
    assert DataSchema.subject_id_name == SubjectSplitSchema.subject_id_name
    assert DataSchema.subject_id_dtype == SubjectSplitSchema.subject_id_dtype
    assert DataSchema.subject_id_name == LabelSchema.subject_id_name
    assert DataSchema.subject_id_dtype == LabelSchema.subject_id_dtype
    assert DataSchema.time_dtype == LabelSchema.prediction_time_dtype


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

    _ = DataSchema.align(pa.Table.from_pylist(raw_data))


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

    _ = CodeMetadataSchema.align(pa.Table.from_pylist(code_metadata))


def test_subject_splits_schema():
    """Test that mock data follows the data schema."""
    # Each element in the list is a row in the table
    subject_splits_data = [
        {"subject_id": 123, "split": train_split},
        {"subject_id": 123, "split": tuning_split},
        {"subject_id": 123, "split": held_out_split},
        {"subject_id": 123, "split": "special"},
    ]

    _ = SubjectSplitSchema.align(pa.Table.from_pylist(subject_splits_data))


def test_label_schema():
    """Test that mock label data follows the label schema."""
    # Each element in the list is a row in the table

    base_label = {
        "subject_id": 123,
        "prediction_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
    }

    for label_col in [
        {"boolean_value": True},
        {"integer_value": 4},
        {"float_value": 0.4},
        {"categorical_value": "text"},
    ]:
        _ = LabelSchema.align(pa.Table.from_pylist([base_label | label_col]))


def test_dataset_metadata_schema():
    """Test that mock metadata follows dataset_metadata schema."""
    metadata = {
        "dataset_name": "Test DataSchemaset",
        "dataset_version": "1.0",
        "etl_name": "Test ETL",
        "etl_version": "1.0",
    }

    try:
        DatasetMetadataSchema.validate(metadata)
        jsonschema.validate(instance=metadata, schema=DatasetMetadataSchema.schema())

        dataset_metadata = DatasetMetadataSchema(**metadata)
        jsonschema.validate(instance=dataset_metadata.to_dict(), schema=DatasetMetadataSchema.schema())
    except Exception as e:
        raise AssertionError(f"DataSchemaset metadata does not follow schema: {e}") from e
