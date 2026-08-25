"""Request payload validation helpers for the SOAR API."""

from typing import Any

# Map JSON schema type names to Python type-check predicates.
# ``integer`` and ``number`` explicitly exclude bool (which is a subclass of int).
_TYPE_CHECKERS: dict[str, Any] = {
    "array": lambda d: isinstance(d, list),
    "object": lambda d: isinstance(d, dict),
    "string": lambda d: isinstance(d, str),
    "integer": lambda d: isinstance(d, int) and not isinstance(d, bool),
    "number": lambda d: isinstance(d, (int, float)) and not isinstance(d, bool),
    "boolean": lambda d: isinstance(d, bool),
    "null": lambda d: d is None,
}


def _type_matches(data: Any, schema_type: Any) -> bool:
    """Check if data matches a JSON schema type declaration."""
    if schema_type is None:
        return True
    if isinstance(schema_type, list):
        return any(_type_matches(data, t) for t in schema_type)
    checker = _TYPE_CHECKERS.get(schema_type)
    return checker(data) if checker else True


def _validate_object(data: dict, schema: dict) -> list[str]:
    """Validate object properties against schema."""
    errors: list[str] = []
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional = schema.get("additionalProperties", True)

    for key in required:
        if key not in data:
            errors.append(f"Missing required property: {key}")

    for key, prop_schema in properties.items():
        if key in data:
            valid, prop_errors = validate_response_schema(data[key], prop_schema)
            if not valid:
                errors.extend(f"{key}: {e}" for e in prop_errors)

    if additional is False:
        for key in data:
            if key not in properties:
                errors.append(f"Unexpected property: {key}")
    return errors


def _validate_array(data: list, schema: dict) -> list[str]:
    """Validate array items against schema."""
    errors: list[str] = []
    items_schema = schema.get("items")
    if items_schema:
        for index, item in enumerate(data):
            valid, item_errors = validate_response_schema(item, items_schema)
            if not valid:
                errors.extend(f"[{index}]: {e}" for e in item_errors)
    return errors


def validate_response_schema(data: Any, schema: Any) -> tuple[bool, list[str]]:
    """Validate data against a simple JSON schema.

    Args:
        data: Data to validate (any type).
        schema: JSON schema dict with ``type``, ``properties``, ``required``.

    Returns:
        tuple: ``(True, [])`` if valid, ``(False, [errors])`` if invalid.
    """
    if not schema or not isinstance(schema, dict):
        return True, []

    errors: list[str] = []

    schema_type = schema.get("type")
    if schema_type is not None and not _type_matches(data, schema_type):
        errors.append(f"Expected type {schema_type}, got {type(data).__name__}")
        return False, errors

    enum_values = schema.get("enum")
    if enum_values is not None and data not in enum_values:
        errors.append(f"Value {data!r} not in enum {enum_values}")

    if isinstance(data, dict):
        errors.extend(_validate_object(data, schema))
    elif isinstance(data, list):
        errors.extend(_validate_array(data, schema))

    return not errors, errors
