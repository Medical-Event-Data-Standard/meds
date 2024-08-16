from meds._version import __version__  # noqa

from .schema import (
    CodeMetadata,
    DatasetMetadata,
    Label,
    birth_code,
    code_field,
    code_metadata_schema,
    data_schema,
    dataset_metadata_schema,
    death_code,
    held_out_split,
    label_schema,
    subject_id_dtype,
    subject_id_field,
    subject_split_schema,
    time_field,
    train_split,
    tuning_split,
)

# List all objects that we want to export
_exported_objects = {
    "data_schema": data_schema,
    "label_schema": label_schema,
    "Label": Label,
    "train_split": train_split,
    "tuning_split": tuning_split,
    "held_out_split": held_out_split,
    "subject_split_schema": subject_split_schema,
    "code_metadata_schema": code_metadata_schema,
    "dataset_metadata_schema": dataset_metadata_schema,
    "CodeMetadata": CodeMetadata,
    "DatasetMetadata": DatasetMetadata,
    "birth_code": birth_code,
    "death_code": death_code,
    "subject_id_field": subject_id_field,
    "time_field": time_field,
    "code_field": code_field,
    "subject_id_dtype": subject_id_dtype,
}

__all__ = list(_exported_objects.keys())
