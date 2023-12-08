# Event Stream Data Standard

The Event Stream Data Standard is a draft data schema for storing streams of medical events, often sourced from either Electronic Health Records or claims records.

The core of the standard is that we define a ``patient`` data structure that contains a series of time stamped events, that in turn contain measurements of various sorts.

The Python type signature for the schema is as follows:

```python

Patient = TypedDict('Patient', {
  'patient_id': int,
  'events': List[Event],
})

Event = TypedDict('Event',{
    'time': datetime.datetime,
    'measurements': List[Measurement],
})

Measurement = TypedDict('Measurement', {
    'code': str,
    'text_value': NotRequired[str],
    'numeric_value': NotRequired[float],
    'datetime_value': NotRequired[datetime.datetime],
    'metadata': NotRequired[Mapping[str, Any]],
})
```

We also provide ETLs to convert common data formats to this schema: https://github.com/Event-Stream-Data-Standard/esds_etl
