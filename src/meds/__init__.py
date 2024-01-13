import warnings

from .schema import (patient_schema, Measurement, Event, Patient, label, Label,
                     code_metadata_entry, code_metadata, dataset_metadata,
                     CodeMetadataEntry, CodeMetadata, DatasetMetadata, birth_code,
                     death_code)


# Define a generic deprecated import function
def _deprecated_import(real_object, warning_message):
    def inner():
        warnings.warn(warning_message, DeprecationWarning, stacklevel=2)
        return real_object
    return inner


# List all the objects that were previously available directly from 'meds'
# These should now be imported from 'meds.schema' instead
_deprecated_objects = {
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

# Apply the deprecation function to all objects
for name, obj in _deprecated_objects.items():
    warning_message = f"Direct import of '{name}' from 'meds' is deprecated and will be removed in a future version. Use 'from meds.schema import {name}' instead."
    globals()[name] = _deprecated_import(obj, warning_message)()

__all__ = list(_deprecated_objects.keys())
