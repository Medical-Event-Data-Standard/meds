from meds._version import __version__

from .schema import (
    CodeMetadataSchema,
    DataSchema,
    DatasetMetadataSchema,
    LabelSchema,
    SubjectSplitSchema,
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
from .validation import CheckResult, ValidationReport, validate_data_shard, validate_dataset
from .validation import main as meds_validate

# List all objects that we want to export
_exported_objects = {
    "CheckResult": CheckResult,
    "ValidationReport": ValidationReport,
    "validate_data_shard": validate_data_shard,
    "validate_dataset": validate_dataset,
    "meds_validate": meds_validate,
    "code_metadata_filepath": code_metadata_filepath,
    "subject_splits_filepath": subject_splits_filepath,
    "dataset_metadata_filepath": dataset_metadata_filepath,
    "data_subdirectory": data_subdirectory,
    "DataSchema": DataSchema,
    "LabelSchema": LabelSchema,
    "train_split": train_split,
    "tuning_split": tuning_split,
    "held_out_split": held_out_split,
    "SubjectSplitSchema": SubjectSplitSchema,
    "CodeMetadataSchema": CodeMetadataSchema,
    "DatasetMetadataSchema": DatasetMetadataSchema,
    "birth_code": birth_code,
    "death_code": death_code,
}

__all__ = list(_exported_objects.keys())
