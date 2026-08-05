from typing import Any, Dict, List, Tuple


def _type_matches(data: Any, schema_type: Any) -> bool:
    """Check if data matches a JSON schema type declaration."""
    if schema_type is None:
        return True
    if isinstance(schema_type, list):
        return any(_type_matches(data, t) for t in schema_type)
    if schema_type == "array":
        return isinstance(data, list)
    if schema_type == "object":
        return isinstance(data, dict)
    if schema_type == "string":
        return isinstance(data, str)
    if schema_type == "integer":
        return isinstance(data, int) and not isinstance(data, bool)
    if schema_type == "number":
        return isinstance(data, (int, float)) and not isinstance(data, bool)
    if schema_type == "boolean":
        return isinstance(data, bool)
    if schema_type == "null":
        return data is None
    return True


def validate_response_schema(data: Any, schema: Any) -> Tuple[bool, List[str]]:
    """Validate data against a simple JSON schema.

    Returns a tuple (is_valid, errors).
    """
    if not schema:
        return True, []

    if not isinstance(schema, dict):
        return True, []

    errors: List[str] = []

    # type
    schema_type = schema.get("type")
    if schema_type is not None and not _type_matches(data, schema_type):
        errors.append(f"Expected type {schema_type}, got {type(data).__name__}")

    if errors:
        return False, errors

    # enum
    enum_values = schema.get("enum")
    if enum_values is not None and data not in enum_values:
        errors.append(f"Value {data!r} not in enum {enum_values}")

    # object properties
    if isinstance(data, dict):
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

    # array items
    if isinstance(data, list):
        items_schema = schema.get("items")
        if items_schema:
            for index, item in enumerate(data):
                valid, item_errors = validate_response_schema(item, items_schema)
                if not valid:
                    errors.extend(f"[{index}]: {e}" for e in item_errors)

    return not errors, errors
