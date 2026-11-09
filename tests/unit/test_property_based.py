#!/usr/bin/env python3
"""Property-based and metamorphic tests (bug-hunt §8.6/§8.10).

Properties verified with Hypothesis:
- sanitizer idempotency (metamorphic) — a second pass must be a no-op
- sanitizer robustness — arbitrary nested payloads never crash
- retry policy call bound — an always-failing callable is invoked
  exactly ``max_attempts`` times
- version-comparison reflexivity and consistency with tuple ordering
- percentile ordering/bounds for execution-time statistics
- translation invariance of extracted node timings (metamorphic)
- IP validator agreement with the stdlib parser (differential)
- response-schema validator never crashes on arbitrary inputs
"""

from __future__ import annotations

import ipaddress
from pathlib import Path

import pytest

hypothesis = pytest.importorskip(
    "hypothesis", reason="hypothesis not installed (stale container image)"
)
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient
from soar_lab.interfaces.api.validation import validate_response_schema
from soar_lab.resilience.retry import RetryPolicy
from soar_lab.security.sanitization import PayloadSanitizer
from soar_lab.validation.validators import IPValidator

_sanitizer = PayloadSanitizer()
_extractor = NodeTimingExtractor()
_thehive = TheHiveClient(base_url="http://localhost:9000", api_key="k", verify_ssl=False)


class TestSanitizerProperties:
    @given(st.text(max_size=500))
    @settings(max_examples=200, deadline=None, suppress_health_check=list(HealthCheck))
    def test_sanitize_is_idempotent(self, text):
        """Metamorphic: sanitize(sanitize(x)) == sanitize(x).

        Catches nested-marker bypasses such as
        ``<scr<script></script>ipt>`` -> ``<script>`` after one pass.
        """
        once = _sanitizer.sanitize(text)
        twice = _sanitizer.sanitize(once)
        assert once == twice

    def test_sanitize_nested_marker_example(self):
        """Concrete regression for the nested-script-tag bypass."""
        payload = "<scr<script></script>ipt>alert(1)</script>"
        result = _sanitizer.sanitize(payload)
        assert "<script" not in result.lower()
        assert _sanitizer.sanitize(result) == result

    def test_sanitize_js_protocol_nested(self):
        """'jjavascript:avascript:' collapses to 'javascript:' in one pass."""
        result = _sanitizer.sanitize("jjavascript:avascript:")
        assert "javascript:" not in result.lower()

    _payloads = st.recursive(
        st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
        lambda children: st.lists(children) | st.dictionaries(st.text(), children),
        max_leaves=20,
    )

    @given(_payloads)
    @settings(
        max_examples=150,
        deadline=None,  # invariant is "never crashes", not speed — 200ms
        # deadline flakes under xdist load without testing the property
        suppress_health_check=[
            HealthCheck.too_slow,
            # pytest-repeat (--count) reruns via distinct executors —
            # differing_executors is a repeat-mechanism artifact, not flakiness
            HealthCheck.differing_executors,
        ],
    )
    def test_sanitize_never_crashes(self, payload):
        _sanitizer.sanitize(payload)


class TestRetryPolicyProperties:
    @given(st.integers(min_value=1, max_value=8))
    def test_always_failing_called_exactly_max_attempts(self, attempts):
        """Call bound: max_attempts=N means exactly N invocations."""
        calls = []

        def fail():
            calls.append(1)
            raise RuntimeError("boom")

        policy = RetryPolicy(max_attempts=attempts, base_delay=0.0)
        with pytest.raises(RuntimeError):
            policy.execute(fail)
        assert len(calls) == attempts

    @given(
        st.integers(min_value=1, max_value=8),
        st.integers(min_value=1, max_value=8),
    )
    def test_eventual_success_call_count(self, attempts, succeed_on):
        """A callable succeeding on attempt k is invoked min(k, attempts) times."""
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < succeed_on:
                raise RuntimeError("boom")
            return "ok"

        policy = RetryPolicy(max_attempts=attempts, base_delay=0.0)
        if succeed_on <= attempts:
            assert policy.execute(flaky) == "ok"
            assert len(calls) == succeed_on
        else:
            with pytest.raises(RuntimeError):
                policy.execute(flaky)
            assert len(calls) == attempts


_version_parts = st.integers(min_value=0, max_value=99)


class TestVersionCompatibilityProperties:
    @given(
        _version_parts,
        _version_parts,
        _version_parts,
    )
    def test_reflexive(self, a, b, c):
        v = f"{a}.{b}.{c}"
        assert _thehive.check_version_compatibility(v, v) is True

    @given(
        st.tuples(_version_parts, _version_parts, _version_parts),
        st.tuples(_version_parts, _version_parts, _version_parts),
    )
    def test_consistent_with_tuple_order(self, cur_t, min_t):
        """Differential: comparison must agree with tuple ordering."""
        cur = ".".join(map(str, cur_t))
        minimum = ".".join(map(str, min_t))
        expected = list(cur_t) >= list(min_t)
        assert _thehive.check_version_compatibility(cur, minimum) is expected

    @given(st.text(max_size=30))
    @settings(max_examples=150)
    def test_unparseable_inputs_never_true(self, text):
        """Any string with no numeric components is unparsable -> False."""
        assume(not any(part.isdigit() for part in text.split(".") if part))
        assert _thehive.check_version_compatibility(text, "1.0.0") is False
        assert _thehive.check_version_compatibility("1.0.0", text) is False


_times = st.lists(st.floats(min_value=0.001, max_value=3599.0), min_size=1, max_size=60)


class TestStatisticalProperties:
    @given(_times)
    def test_percentiles_ordered_and_bounded(self, times):
        m = StatisticalCalculator.calculate_statistical_metrics(times)
        assert m["min"] <= m["p50"] <= m["p90"] <= m["p95"] <= m["p99"] <= m["max"]
        assert m["total_executions"] == len(times)
        assert m["p50"] == m["median"]

    @given(_times)
    def test_min_max_consistent(self, times):
        m = StatisticalCalculator.calculate_statistical_metrics(times)
        assert abs(m["min"] - round(min(times), 2)) < 0.01
        assert abs(m["max"] - round(max(times), 2)) < 0.01


class TestTimingExtractorMetamorphic:
    @given(
        st.floats(min_value=1e9, max_value=2e9),
        st.floats(min_value=0.0, max_value=1e6),
    )
    def test_translation_invariant_durations(self, base, delta):
        """Metamorphic: shifting every timestamp by delta preserves durations."""
        node_start_ms = (base + 1) * 1000
        node_end_ms = (base + 3) * 1000
        execution = {
            "execution_id": "x",
            "started_at": base,
            "completed_at": base + 10,
            "results": [
                {
                    "action": {"label": "n1"},
                    "started_at": node_start_ms,
                    "completed_at": node_end_ms,
                    "status": "SUCCESS",
                }
            ],
        }
        shifted = {
            "execution_id": "x",
            "started_at": base + delta,
            "completed_at": base + delta + 10,
            "results": [
                {
                    "action": {"label": "n1"},
                    "started_at": node_start_ms + delta * 1000,
                    "completed_at": node_end_ms + delta * 1000,
                    "status": "SUCCESS",
                }
            ],
        }
        a = _extractor.extract_timings(execution)
        b = _extractor.extract_timings(shifted)
        assert a["nodes"]["n1"]["duration_s"] == pytest.approx(
            b["nodes"]["n1"]["duration_s"], abs=0.01
        )
        assert a["workflow_duration_s"] == pytest.approx(b["workflow_duration_s"], abs=0.01)


class TestIPValidatorDifferential:
    @given(
        st.tuples(
            st.integers(min_value=0, max_value=999),
            st.integers(min_value=0, max_value=999),
            st.integers(min_value=0, max_value=999),
            st.integers(min_value=0, max_value=999),
        ),
        st.booleans(),
    )
    @settings(max_examples=300)
    def test_agrees_with_stdlib(self, octets, pad):
        """Differential vs ``ipaddress``: leading zeros are octal-ambiguous
        and must be rejected exactly like the stdlib parser does."""
        parts = [str(o).zfill(3) if pad else str(o) for o in octets]
        candidate = ".".join(parts)
        try:
            ipaddress.IPv4Address(candidate)
            stdlib_ok = True
        except ValueError:
            stdlib_ok = False
        assert IPValidator.validate(candidate) is stdlib_ok


class TestFilesystemKeyConfinement:
    """BL-FS-005 — adversarial property: no storage key escapes the base.

    For ANY string — traversal segments, absolutes, unicode, separators —
    the resolved path must either raise UnsafeStorageKey or land inside
    ``base``. An escape is a write-outside-sandbox vulnerability.
    """

    @staticmethod
    def _storage():
        import tempfile

        from soar_lab.infrastructure.filesystem_storage import FilesystemStorage

        base = Path(tempfile.mkdtemp()).resolve()
        return FilesystemStorage(base_dir=str(base)), base

    @given(st.text(max_size=200))
    @settings(max_examples=400, deadline=None, suppress_health_check=list(HealthCheck))
    def test_no_key_escapes_base(self, key):
        import os

        from soar_lab.infrastructure.filesystem_storage import UnsafeStorageKey

        storage, base = self._storage()
        try:
            resolved = storage._resolve_key(key)
        except UnsafeStorageKey:
            return  # rejection is a valid outcome
        assert str(resolved).startswith(str(base) + os.sep)

    @given(
        st.lists(
            st.text(
                alphabet="abcXYZ09/\\._~ー中",
                min_size=0,
                max_size=12,
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=300, deadline=None, suppress_health_check=list(HealthCheck))
    def test_segment_joins_stay_confined(self, segments):
        """Multi-segment joins (the traversal vector class) never escape."""
        import os

        from soar_lab.infrastructure.filesystem_storage import UnsafeStorageKey

        storage, base = self._storage()
        key = "/".join(segments)
        try:
            resolved = storage._resolve_key(key)
        except UnsafeStorageKey:
            return
        assert str(resolved).startswith(str(base) + os.sep)


class TestSchemaValidatorRobustness:
    _data = st.recursive(
        st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
        lambda children: st.lists(children, max_size=5)
        | st.dictionaries(st.text(), children, max_size=5),
        max_leaves=15,
    )

    @given(_data)
    # too_slow: recursive generation occasionally stalls under load
    # (suite run in parallel with Docker E2E); the property under test
    # is crash-freedom, not generation speed.
    @settings(
        max_examples=150,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
    )
    def test_validate_never_crashes(self, data):
        ok, errors = validate_response_schema(data, {"type": "object"})
        assert isinstance(ok, bool)
        assert isinstance(errors, list)


class TestDotenvLookupProperties:
    """dotenv_lookup invariants — exact-key match, first '=' split,
    comment/blank skipping, quote stripping."""

    @given(
        key=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_", min_size=1, max_size=20),
        value=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=0, max_size=30),
    )
    @settings(max_examples=200, deadline=None)
    def test_roundtrip_exact_key(self, key, value):
        import tempfile

        assume(key[0].isalpha())
        from soar_lab.common.runtime import dotenv_lookup

        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env.test"
            env.write_text(f"{key}={value}\n", encoding="utf-8")
            assert dotenv_lookup(env, key) == value

    @given(key=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=2, max_size=15))
    @settings(max_examples=100, deadline=None)
    def test_prefix_never_matches(self, key):
        """A query for a *prefix* of a stored key must return ''."""
        import tempfile

        from soar_lab.common.runtime import dotenv_lookup

        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env.test"
            env.write_text(f"{key}X=secret\n", encoding="utf-8")
            assert dotenv_lookup(env, key) == ""

    def test_first_equals_splits(self):
        import tempfile

        from soar_lab.common.runtime import dotenv_lookup

        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env.test"
            env.write_text("URL=https://x:443/path?a=b\n", encoding="utf-8")
            assert dotenv_lookup(env, "URL") == "https://x:443/path?a=b"


class TestHashValidatorProperties:
    """Differential: every random hex string of the right length is a
    valid digest — including all-digit hex (the old isdigit() bug)."""

    @given(
        length=st.sampled_from([32, 40, 64]),
        hexdigits=st.text(alphabet="0123456789abcdefABCDEF", min_size=1, max_size=1),
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_hex_lengths_accepted(self, length, hexdigits):
        from soar_lab.validation.validators import HashValidator

        assert HashValidator.validate(hexdigits * length) is True

    @given(
        length=st.sampled_from([32, 40, 64]),
        digit=st.text(alphabet="0123456789", min_size=1, max_size=1),
    )
    @settings(max_examples=30, deadline=None)
    def test_all_digit_hex_accepted(self, length, digit):
        """Regression guard: all-decimal digests ARE valid hex."""
        from soar_lab.validation.validators import HashValidator

        assert HashValidator.validate(digit * length) is True

    @given(
        length=st.integers(min_value=1, max_value=128).filter(lambda n: n not in (32, 40, 64)),
        ch=st.text(alphabet="0123456789abcdef", min_size=1, max_size=1),
    )
    @settings(max_examples=60, deadline=None)
    def test_wrong_lengths_rejected(self, length, ch):
        from soar_lab.validation.validators import HashValidator

        assert HashValidator.validate(ch * length) is False
