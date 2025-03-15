from meds._version import __version__  # noqa

from .schema import (
    CodeMetadata,
    Data,
    DatasetMetadata,
    Label,
    SubjectSplit,
    birth_code,
    code_metadata_filepath,
    data_subdirectory,
    dataset_metadata_filepath,
    death_code,
    held_out_split,
    subject_splits_filepath,
    train_split,
    tuning_split,
)

# List all objects that we want to export
_exported_objects = {
    "code_metadata_filepath": code_metadata_filepath,
    "subject_splits_filepath": subject_splits_filepath,
    "dataset_metadata_filepath": dataset_metadata_filepath,
    "data_subdirectory": data_subdirectory,
    "Data": Data,
    "Label": Label,
    "train_split": train_split,
    "tuning_split": tuning_split,
    "held_out_split": held_out_split,
    "SubjectSplit": SubjectSplit,
    "CodeMetadata": CodeMetadata,
    "DatasetMetadata": DatasetMetadata,
    "birth_code": birth_code,
    "death_code": death_code,
}

__all__ = list(_exported_objects.keys())
