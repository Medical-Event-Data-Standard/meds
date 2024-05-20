# Medical Event Data Standard

The Medical Event Data Standard (MEDS) is a draft data schema for storing streams of medical events, often sourced from either Electronic Health Records or claims records.

The core of the standard is that we define a ``patient`` data structure that contains a series of time stamped events, that in turn contain measurements of various sorts.

The Python type signature for the schema is as follows:

```python

Patient = TypedDict('Patient', {
  'patient_id': int,
  'events': List[Event],
})

Event = TypedDict('Event',{
    'time': NotRequired[datetime.datetime], # Static events will have a null timestamp here
    'code': str,
    'text_value': NotRequired[str],
    'numeric_value': NotRequired[float],
    'datetime_value': NotRequired[datetime.datetime],
    'metadata': NotRequired[Mapping[str, Any]],
})
```

Example patient following this schema

```python

patient_data = {
  "patient_id": 123,
  "events": [
    # Store static events like gender with a null timestamp
    {
        "time": None,
        "code": "Gender/F",
    },

    # It's recommended to record birth using the birth_code
    {
      "time": datetime.datetime(1995, 8, 20),
      "code": meds.birth_code,
    },

    # Arbitrary events with sophisticated data can also be added
    {
        "time": datetime.datetime(2020, 1, 1, 12, 0, 0),
        "code": "some_code",
        "text_value": "Example",
        "numeric_value": 10.0,
        "datetime_value": datetime.datetime(2020, 1, 1, 12, 0, 0),
        "properties": None
    },
  ]
}

```

We also provide ETLs to convert common data formats to this schema: https://github.com/Medical-Event-Data-Standard/meds_etl
