"""A simple class for flexible schema definition and usage."""

import datetime
from dataclasses import MISSING, asdict, dataclass, field, fields
from typing import Any, ClassVar, Dict, List, Union, get_args, get_origin

import pyarrow as pa

PYTHON_TO_PYARROW = {
    int: pa.int64(),
    float: pa.float32(),
    str: pa.string(),
    bool: pa.bool_(),
    datetime.datetime: pa.timestamp("us"),
    list[str]: pa.list_(pa.string()),  # This likely won't work
}
PYTHON_TO_JSON = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    datetime.datetime: "string",  # datetime as ISO8601 string
}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISO8601 format


class MEDSValidationError(Exception):
    pass


def with_field_names_and_types(cls):
    """A class decorator that adds field name and PyArrow type attributes to a dataclass.

    This provides a convenient way to access the field names and PyArrow types of a schema class without
    needing to separately export strings or types.

    An example usage is shown in the docstring of the `Schema` class.
    """

    for f in fields(cls):
        if f.name == "_extra_fields":
            continue
        setattr(cls, f"{f.name}_name", f.name)
        base_type = get_args(f.type)[0] if Schema._is_optional(f.type) else f.type
        arrow_dtype = PYTHON_TO_PYARROW.get(base_type, pa.string())
        setattr(cls, f"{f.name}_dtype", arrow_dtype)
    return cls


@dataclass
class Schema:
    """A flexible mixin Schema class for easy definition of flexible, readable MEDS schemas.

    To use this class, initiate a subclass with the desired fields as dataclass fields. Fields will be
    re-mapped to PyArrow types via the `PYTHON_TO_PYARROW` dictionary. The resulting object can then be used
    to validate and reformat PyArrow tables to a validated form, or used for type-safe dictionary-like usage
    of data conforming to the schema.

    Example usage:
        >>> from typing import Optional
        >>> @with_field_names_and_types
        ... @dataclass
        ... class Data(Schema):
        ...     allow_extra_columns: ClassVar[bool] = True
        ...     subject_id: int
        ...     time: datetime.datetime
        ...     code: str
        ...     numeric_value: Optional[float] = None
        ...     text_value: Optional[str] = None
        >>> Data.subject_id_name
        'subject_id'
        >>> Data.subject_id_dtype
        DataType(int64)
        >>> Data.time_name
        'time'
        >>> Data.time_dtype
        TimestampType(timestamp[us])
        >>> data = Data(subject_id=1, time=datetime.datetime(2025, 3, 7, 16), code="A", numeric_value=1.0)
        >>> data # doctest: +NORMALIZE_WHITESPACE
        Data(subject_id=1,
             time=datetime.datetime(2025, 3, 7, 16, 0),
             code='A',
             numeric_value=1.0,
             text_value=None)
        >>> data_tbl = pa.Table.from_pydict({
        ...     "time": [
        ...         datetime.datetime(2021, 3, 1),
        ...         datetime.datetime(2021, 4, 1),
        ...         datetime.datetime(2021, 5, 1),
        ...     ],
        ...     "subject_id": [1, 2, 3],
        ...     "code": ["A", "B", "C"],
        ... })
        >>> Data.validate(data_tbl)
        pyarrow.Table
        subject_id: int64
        time: timestamp[us]
        code: string
        numeric_value: float
        text_value: string
        ----
        subject_id: [[1,2,3]]
        time: [[2021-03-01 00:00:00.000000,2021-04-01 00:00:00.000000,2021-05-01 00:00:00.000000]]
        code: [["A","B","C"]]
        numeric_value: [[null,null,null]]
        text_value: [[null,null,null]]
        >>> data_tbl_with_extra = pa.Table.from_pydict({
        ...     "time": [
        ...         datetime.datetime(2021, 3, 1),
        ...         datetime.datetime(2021, 4, 1),
        ...     ],
        ...     "subject_id": [4, 5],
        ...     "extra_1": ["extra1", "extra2"],
        ...     "extra_2": [452, 11],
        ...     "code": ["D", "E"],
        ... })
        >>> Data.validate(data_tbl_with_extra)
        pyarrow.Table
        subject_id: int64
        time: timestamp[us]
        code: string
        numeric_value: float
        text_value: string
        extra_1: string
        extra_2: int64
        ----
        subject_id: [[4,5]]
        time: [[2021-03-01 00:00:00.000000,2021-04-01 00:00:00.000000]]
        code: [["D","E"]]
        numeric_value: [[null,null]]
        text_value: [[null,null]]
        extra_1: [["extra1","extra2"]]
        extra_2: [[452,11]]
        >>> Data.to_json_schema() # doctest: +NORMALIZE_WHITESPACE
        {'type': 'object',
         'properties': {'subject_id': {'type': 'integer'},
                        'time': {'type': 'string', 'format': 'date-time'},
                        'code': {'type': 'string'},
                        'numeric_value': {'type': 'number'},
                        'text_value': {'type': 'string'}},
         'required': ['subject_id', 'time', 'code'],
         'additionalProperties': True}
    """

    allow_extra_columns: ClassVar[bool] = True
    _extra_fields: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        defined_field_names = {f.name for f in fields(self)}
        if self.allow_extra_columns:
            # Identify and store any extra fields provided at initialization
            provided_fields = set(self.__dict__.keys())
            extra_fields = provided_fields - defined_field_names - {"_extra_fields"}
            for field_name in extra_fields:
                self._extra_fields[field_name] = self.__dict__.pop(field_name)
        else:
            provided_fields = set(self.__dict__.keys())
            extra_fields = provided_fields - defined_field_names - {"_extra_fields"}
            if extra_fields:
                raise MEDSValidationError(f"Unexpected extra fields provided: {extra_fields}")

    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        elif self.allow_extra_columns and key in self._extra_fields:
            return self._extra_fields[key]
        else:
            raise KeyError(f"{key} not found in schema.")

    def __setitem__(self, key, value):
        if key in {f.name for f in fields(self)}:
            setattr(self, key, value)
        elif self.allow_extra_columns:
            self._extra_fields[key] = value
        else:
            raise MEDSValidationError(f"Extra fields not allowed, got '{key}'.")

    def keys(self):
        return list({f.name for f in fields(self)} | self._extra_fields.keys())

    def values(self):
        return [self[k] for k in self.keys()]

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def __iter__(self):
        return iter(self.keys())

    def to_dict(self) -> Dict[str, Any]:
        out = {**asdict(self), **self._extra_fields}
        return {k: v for k, v in out.items() if v is not MISSING and v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        field_names = {f.name for f in fields(cls)}
        known_fields = {k: v for k, v in data.items() if k in field_names}
        instance = cls(**known_fields)
        extra_fields = {k: v for k, v in data.items() if k not in field_names}
        if extra_fields:
            if cls.allow_extra_columns:
                instance._extra_fields = extra_fields
            else:
                raise MEDSValidationError(f"Unexpected extra fields provided: {set(extra_fields)}")
        return instance

    @classmethod
    def _is_optional(cls, annotation) -> bool:
        return get_origin(annotation) is Union and type(None) in get_args(annotation)

    @classmethod
    def pyarrow_schema(cls) -> pa.Schema:
        arrow_fields = []
        for f in fields(cls):
            optional = cls._is_optional(f.type)
            base_type = get_args(f.type)[0] if optional else f.type
            arrow_type = PYTHON_TO_PYARROW.get(base_type, pa.string())
            arrow_fields.append(pa.field(f.name, arrow_type, nullable=optional))
        return pa.schema(arrow_fields)

    @classmethod
    def validate(
        cls, table: Union[pa.Table, Dict[str, List[Any]]], reorder_columns: bool = True, cast_types: bool = True
    ) -> pa.Table:
        if isinstance(table, dict):
            table = pa.Table.from_pydict(table)

        table_cols = set(table.column_names)
        mandatory_cols = {f.name for f in fields(cls) if not cls._is_optional(f.type)} - {"_extra_fields"}
        all_defined_cols = {f.name for f in fields(cls)}

        missing_cols = mandatory_cols - table_cols
        if missing_cols:
            raise MEDSValidationError(f"Missing mandatory columns: {missing_cols}")

        extra_cols = table_cols - all_defined_cols
        if extra_cols and not cls.allow_extra_columns:
            raise MEDSValidationError(f"Unexpected extra columns: {extra_cols}")

        # Add missing optional cols with default None
        for f in fields(cls):
            if f.name == "_extra_fields":
                continue
            if f.name not in table_cols:
                length = table.num_rows
                optional = cls._is_optional(f.type)
                base_type = get_args(f.type)[0] if optional else f.type
                arrow_type = PYTHON_TO_PYARROW.get(base_type, pa.string())
                table = table.append_column(f.name, pa.array([None] * length, type=arrow_type))

        # Reorder columns
        if reorder_columns:
            ordered_cols = [f.name for f in fields(cls) if f.name in table.column_names]
            if cls.allow_extra_columns:
                ordered_cols += [c for c in table.column_names if c not in ordered_cols]
            table = table.select(ordered_cols)

        # Cast columns if needed
        if cast_types:
            for f in fields(cls):
                if f.name == "_extra_fields":
                    continue
                optional = cls._is_optional(f.type)
                base_type = get_args(f.type)[0] if optional else f.type
                expected_type = PYTHON_TO_PYARROW.get(base_type, pa.string())
                current_type = table.schema.field(f.name).type
                if current_type != expected_type:
                    try:
                        table = table.set_column(
                            table.schema.get_field_index(f.name), f.name, table.column(f.name).cast(expected_type)
                        )
                    except pa.ArrowInvalid as e:
                        raise MEDSValidationError(f"Column '{f.name}' cast failed: {e}")

        return table

    @classmethod
    def to_json_schema(cls) -> Dict[str, Any]:
        schema_properties = {}
        required_fields = []

        for f in fields(cls):
            if f.name == "_extra_fields":
                continue
            optional = cls._is_optional(f.type)
            base_type = get_args(f.type)[0] if optional else f.type
            json_type = PYTHON_TO_JSON.get(base_type, "string")

            property_schema = {"type": json_type}

            # Special handling for datetime
            if base_type is datetime.datetime:
                property_schema["format"] = "date-time"

            schema_properties[f.name] = property_schema

            if not optional:
                required_fields.append(f.name)

        schema = {
            "type": "object",
            "properties": schema_properties,
            "required": required_fields,
            "additionalProperties": cls.allow_extra_columns,
        }

        return schema
