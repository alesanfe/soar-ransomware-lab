"""
Shared assertions for persistence validation in E2E tests.
"""

from typing import Dict, List, Any


def assert_data_persisted(system: str, data: Dict[str, Any]):
    """Assert that data was persisted in a system."""
    assert data is not None, f"Data not persisted in {system}"
    assert len(data) > 0, f"Empty data persisted in {system}"


def assert_data_integrity(original: Dict[str, Any], persisted: Dict[str, Any], fields: List[str]):
    """Assert that specified fields are preserved between original and persisted data."""
    for field in fields:
        original_value = original.get(field)
        persisted_value = persisted.get(field)
        assert original_value == persisted_value, f"Field {field} changed: {original_value} -> {persisted_value}"


def assert_no_data_loss(original_count: int, persisted_count: int):
    """Assert that no data was lost during persistence."""
    assert persisted_count >= original_count, f"Data loss: {original_count} -> {persisted_count}"


def assert_data_recoverable(system: str, key: str, data: Dict[str, Any]):
    """Assert that data can be recovered from a system by key."""
    assert key in data, f"Key {key} not found in {system} data"
    assert data[key] is not None, f"Data for key {key} is None in {system}"


def assert_backup_checksum(original_checksum: str, backup_checksum: str):
    """Assert that backup checksum matches original."""
    assert original_checksum == backup_checksum, f"Checksum mismatch: {original_checksum} != {backup_checksum}"


def assert_data_not_corrupted(data: Dict[str, Any]):
    """Assert that data is not corrupted (basic checks)."""
    assert data is not None, "Data is None (corrupted)"
    assert isinstance(data, dict), f"Data is not a dict: {type(data)}"
    assert len(data) > 0, "Data is empty (corrupted)"
