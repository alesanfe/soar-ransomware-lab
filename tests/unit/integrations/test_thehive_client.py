"""Unit tests for TheHiveClient pure-logic helpers."""

from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


def _make_client() -> TheHiveClient:
    return TheHiveClient(base_url="http://localhost:9000", api_key="k", verify_ssl=False)


def test_check_version_compatibility_unequal_lengths():
    """Bug: '5.1' vs '5.1.0' compares [5,1] >= [5,1,0] -> False though
    they are the same semver; padding to equal length is required."""
    client = _make_client()
    assert client.check_version_compatibility("5.1", "5.1.0") is True
    assert client.check_version_compatibility("5.1.0", "5.1") is True
    assert client.check_version_compatibility("5.1.1", "5.1") is True
    assert client.check_version_compatibility("5.1", "5.1.1") is False


def test_check_version_compatibility_unparseable():
    """Bug: parse('abc') -> [] padded to [0,0], so '5.1' >= 'abc' returns True
    though the docstring promises False when either version is unparsable."""
    client = _make_client()
    assert client.check_version_compatibility("5.1", "abc") is False
    assert client.check_version_compatibility("abc", "5.1") is False
    assert client.check_version_compatibility("", "5.1") is False
    assert client.check_version_compatibility("5.1", "") is False
