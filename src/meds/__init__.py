import warnings

from .schema import (patient_schema, Measurement, Event, Patient, label, Label,
                     code_metadata_entry, code_metadata, dataset_metadata,
                     CodeMetadataEntry, CodeMetadata, DatasetMetadata, birth_code,
                     death_code)


# List all objects that we want to export
_exported_objects = {
    'patient_schema': patient_schema,
    'Measurement': Measurement,
    'Event': Event,
    'Patient': Patient,
    'label': label,
    'Label': Label,
    'code_metadata_entry': code_metadata_entry,
    'code_metadata': code_metadata,
    'dataset_metadata': dataset_metadata,
    'CodeMetadataEntry': CodeMetadataEntry,
    'CodeMetadata': CodeMetadata,
    'DatasetMetadata': DatasetMetadata,
    'birth_code': birth_code,
    'death_code': death_code
}

__all__ = list(_exported_objects.keys())
