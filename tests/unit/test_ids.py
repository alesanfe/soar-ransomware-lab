"""Unit tests for RFC 9562 UUIDv7 generation (soar_lab.common.ids)."""

import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from soar_lab.common.ids import new_id, new_uuid7, uuid7, uuid7_hex


class TestUuid7Format:
    def test_is_valid_uuid(self):
        u = uuid7()
        assert isinstance(u, uuid.UUID)
        assert u.version == 7

    def test_variant_bits(self):
        # RFC 4122 variant: bits 10x in octet 8.
        assert uuid7().bytes[8] & 0xC0 == 0x80

    def test_hex_is_32_chars(self):
        h = uuid7_hex()
        assert len(h) == 32
        assert re.fullmatch(r"[0-9a-f]{32}", h)

    def test_embeds_unix_ms_timestamp(self):
        before = int(time.time() * 1000)
        u = uuid7()
        after = int(time.time() * 1000)
        ts_ms = u.int >> 80
        assert before <= ts_ms <= after + 1


class TestOrdering:
    def test_lexicographic_order_matches_generation_order(self):
        ids = [uuid7_hex() for _ in range(50)]
        assert ids == sorted(ids)

    def test_monotonic_within_same_millisecond(self):
        # Force many ids in one ms — the rand_a counter keeps them ordered.
        ids = [uuid7().hex for _ in range(100)]
        assert ids == sorted(ids)
        assert len(set(ids)) == 100


class TestUniqueness:
    def test_no_collisions_sequential(self):
        ids = {uuid7_hex() for _ in range(2000)}
        assert len(ids) == 2000

    def test_no_collisions_concurrent(self):
        with ThreadPoolExecutor(max_workers=8) as ex:
            ids = list(ex.map(lambda _: uuid7_hex(), range(2000)))
        assert len(set(ids)) == 2000


class TestNewId:
    def test_prefixed_form(self):
        i = new_id("alr")
        assert i.startswith("alr-")
        assert re.fullmatch(r"alr-[0-9a-f]{32}", i)

    def test_unprefixed_is_plain_hex(self):
        i = new_id()
        assert re.fullmatch(r"[0-9a-f]{32}", i)

    def test_prefixed_ids_sort_chronologically(self):
        ids = [new_id("adm") for _ in range(20)]
        assert ids == sorted(ids)

    def test_alias(self):
        assert isinstance(new_uuid7(), uuid.UUID)
