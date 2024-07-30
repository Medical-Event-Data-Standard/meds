from meds._version import __version__  # noqa

from .schema import (
    data_schema, label_schema, Label, train_split, tuning_split, held_out_split, patient_split_schema,
    code_metadata_schema, dataset_metadata_schema, CodeMetadata, DatasetMetadata, birth_code, death_code
)


# List all objects that we want to export
_exported_objects = {
    'data_schema': data_schema,
    'label_schema': label_schema,
    'Label': Label,
    'train_split': train_split,
    'tuning_split': tuning_split,
    'held_out_split': held_out_split,
    'patient_split_schema': patient_split_schema,
    'code_metadata_schema': code_metadata_schema,
    'dataset_metadata_schema': dataset_metadata_schema,
    'CodeMetadata': CodeMetadata,
    'DatasetMetadata': DatasetMetadata,
    'birth_code': birth_code,
    'death_code': death_code,
}

__all__ = list(_exported_objects.keys())
