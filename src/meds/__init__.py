from meds._version import __version__  # noqa

from .schema import (
    data, label, Label, train_split, tuning_split, held_out_split, patient_split, code_metadata,
    dataset_metadata, CodeMetadata, DatasetMetadata, birth_code, death_code
)


# List all objects that we want to export
_exported_objects = {
    'data': data,
    'label': label,
    'Label': Label,
    'train_split': train_split,
    'tuning_split': tuning_split,
    'held_out_split': held_out_split,
    'patient_split': patient_split,
    'code_metadata': code_metadata,
    'dataset_metadata': dataset_metadata,
    'CodeMetadata': CodeMetadata,
    'DatasetMetadata': DatasetMetadata,
    'birth_code': birth_code,
    'death_code': death_code,
}

__all__ = list(_exported_objects.keys())
