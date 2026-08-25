"""Unit tests for interfaces.api.validation schema validator.

Covers _type_matches, _validate_object, _validate_array,
validate_response_schema.
"""

from __future__ import annotations

from soar_lab.interfaces.api.validation import (
    _type_matches,
    _validate_array,
    _validate_object,
    validate_response_schema,
)


class TestTypeMatches:
    """Tests for _type_matches."""

    def test_none_schema_type_returns_true(self):
        assert _type_matches("anything", None) is True

    def test_string_type(self):
        assert _type_matches("hello", "string") is True
        assert _type_matches(123, "string") is False

    def test_integer_type_excludes_bool(self):
        assert _type_matches(42, "integer") is True
        assert _type_matches(True, "integer") is False
        assert _type_matches(3.14, "integer") is False

    def test_number_type_excludes_bool(self):
        assert _type_matches(42, "number") is True
        assert _type_matches(3.14, "number") is True
        assert _type_matches(True, "number") is False

    def test_boolean_type(self):
        assert _type_matches(True, "boolean") is True
        assert _type_matches(False, "boolean") is True
        assert _type_matches(1, "boolean") is False

    def test_array_type(self):
        assert _type_matches([1, 2], "array") is True
        assert _type_matches("not list", "array") is False

    def test_object_type(self):
        assert _type_matches({"a": 1}, "object") is True
        assert _type_matches([1, 2], "object") is False

    def test_null_type(self):
        assert _type_matches(None, "null") is True
        assert _type_matches(0, "null") is False

    def test_list_of_types(self):
        assert _type_matches("hello", ["string", "integer"]) is True
        assert _type_matches(42, ["string", "integer"]) is True
        assert _type_matches(True, ["string", "integer"]) is False

    def test_unknown_type_returns_true(self):
        assert _type_matches("anything", "unknown_type") is True


class TestValidateObject:
    """Tests for _validate_object."""

    def test_valid_object(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        errors = _validate_object({"name": "Alice", "age": 30}, schema)
        assert errors == []

    def test_missing_required(self):
        schema = {"required": ["name"]}
        errors = _validate_object({}, schema)
        assert len(errors) == 1
        assert "Missing required property: name" in errors[0]

    def test_additional_properties_false(self):
        schema = {
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        errors = _validate_object({"name": "Alice", "extra": "bad"}, schema)
        assert any("Unexpected property" in e for e in errors)

    def test_additional_properties_allowed(self):
        schema = {"properties": {"name": {"type": "string"}}}
        errors = _validate_object({"name": "Alice", "extra": "ok"}, schema)
        assert errors == []

    def test_nested_validation_error(self):
        schema = {
            "properties": {"age": {"type": "integer"}},
        }
        errors = _validate_object({"age": "not int"}, schema)
        assert any("age:" in e for e in errors)


class TestValidateArray:
    """Tests for _validate_array."""

    def test_valid_array(self):
        schema = {"items": {"type": "string"}}
        errors = _validate_array(["a", "b", "c"], schema)
        assert errors == []

    def test_invalid_array_items(self):
        schema = {"items": {"type": "string"}}
        errors = _validate_array(["a", 123, "c"], schema)
        assert len(errors) == 1
        assert "[1]" in errors[0]

    def test_empty_array(self):
        schema = {"items": {"type": "string"}}
        errors = _validate_array([], schema)
        assert errors == []

    def test_no_items_schema(self):
        errors = _validate_array([1, 2, 3], {})
        assert errors == []


class TestValidateResponseSchema:
    """Tests for validate_response_schema."""

    def test_empty_schema_returns_valid(self):
        valid, errors = validate_response_schema({"any": "thing"}, {})
        assert valid is True
        assert errors == []

    def test_non_dict_schema_returns_valid(self):
        valid, errors = validate_response_schema("data", "not a dict")
        assert valid is True
        assert errors == []

    def test_type_mismatch(self):
        valid, errors = validate_response_schema("hello", {"type": "integer"})
        assert valid is False
        assert "Expected type integer" in errors[0]

    def test_enum_validation(self):
        valid, errors = validate_response_schema("c", {"enum": ["a", "b"]})
        assert valid is False
        assert "not in enum" in errors[0]

    def test_enum_valid_value(self):
        valid, errors = validate_response_schema("a", {"enum": ["a", "b"]})
        assert valid is True

    def test_complex_schema_valid(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        }
        valid, errors = validate_response_schema({"name": "test", "tags": ["a", "b"]}, schema)
        assert valid is True
        assert errors == []

    def test_complex_schema_invalid(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        }
        valid, errors = validate_response_schema({"tags": [1, 2]}, schema)
        assert valid is False
        assert any("Missing required" in e for e in errors)
        assert any("[0]" in e for e in errors)
