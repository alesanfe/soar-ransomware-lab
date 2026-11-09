#!/usr/bin/env python3
"""Unit tests for RedisAdmissionStore — Redis client fully mocked.

Covers the hash-mapping codec (dicts/lists serialized as JSON, scalars
as str), the vanish-before-update guard, the SET NX winner/loser split
and the compare-and-delete unbind. No Redis server needed.
"""

from unittest.mock import AsyncMock

import pytest

from soar_lab.infrastructure.messaging.redis_admission_store import (
    RedisAdmissionStore,
)


@pytest.fixture
def client():
    return AsyncMock()


@pytest.fixture
def store(client):
    return RedisAdmissionStore(client, record_ttl_s=3600)


class TestCreate:
    async def test_create_writes_hash_and_ttl(self, store, client):
        await store.create({"admission_id": "adm-1", "status": "queued", "meta": {"a": 1}, "n": 5})
        key = "soar:admission:adm-1"
        client.hset.assert_awaited_once()
        call = client.hset.await_args
        assert call.args[0] == key
        assert call.kwargs["mapping"]["status"] == "queued"
        assert call.kwargs["mapping"]["meta"] == '{"a": 1}'
        assert call.kwargs["mapping"]["n"] == "5"
        client.expire.assert_awaited_once_with(key, 3600)


class TestUpdate:
    async def test_update_writes_fields_when_record_exists(self, store, client):
        client.exists.return_value = 1
        await store.update("adm-1", {"status": "forwarded"})
        client.hset.assert_awaited_once()
        assert client.hset.await_args.kwargs["mapping"]["status"] == "forwarded"

    async def test_update_skips_and_warns_when_record_vanished(self, store, client):
        client.exists.return_value = 0
        await store.update("adm-gone", {"status": "forwarded"})
        client.hset.assert_not_awaited()


class TestGet:
    async def test_get_returns_none_for_missing(self, store, client):
        client.hgetall.return_value = {}
        assert await store.get("nope") is None

    async def test_get_decodes_bytes_and_json(self, store, client):
        client.hgetall.return_value = {
            b"status": b"queued",
            "meta": b'{"a": 1}',
            "n": b"7",
        }
        out = await store.get("adm-1")
        assert out["status"] == "queued"
        assert out["meta"] == {"a": 1}
        assert out["n"] == 7  # "7" is valid JSON int

    async def test_get_keeps_unparseable_values_as_str(self, store, client):
        client.hgetall.return_value = {"last_error": b"not-json{["}
        out = await store.get("adm-1")
        assert out["last_error"] == "not-json{["


class TestIdempotencyKeys:
    async def test_find_by_key_missing(self, store, client):
        client.get.return_value = None
        assert await store.find_by_key("k1") is None

    async def test_find_by_key_decodes_bytes(self, store, client):
        client.get.return_value = b"adm-9"
        assert await store.find_by_key("k1") == "adm-9"

    async def test_bind_key_sets_nx_with_ttl(self, store, client):
        await store.bind_key("k1", "adm-1")
        client.set.assert_awaited_once_with("soar:admission:key:k1", "adm-1", ex=3600, nx=True)

    async def test_try_bind_winner_returns_none(self, store, client):
        client.set.return_value = True
        assert await store.try_bind_key("k1", "adm-1") is None

    async def test_try_bind_loser_returns_existing_admission(self, store, client):
        client.set.return_value = None
        client.get.return_value = b"adm-first"
        assert await store.try_bind_key("k1", "adm-2") == "adm-first"

    async def test_try_bind_loser_without_record_falls_back(self, store, client):
        client.set.return_value = None
        client.get.return_value = None
        assert await store.try_bind_key("k1", "adm-2") == "adm-2"

    async def test_unbind_uses_compare_and_delete_script(self, store, client):
        await store.unbind_key("k1", "adm-1")
        client.eval.assert_awaited_once()
        script, nkeys, key, arg = client.eval.await_args.args
        assert "GET" in script and "DEL" in script
        assert nkeys == 1
        assert key == "soar:admission:key:k1"
        assert arg == "adm-1"
