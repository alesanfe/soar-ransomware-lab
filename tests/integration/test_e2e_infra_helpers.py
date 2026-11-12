#!/usr/bin/env python3
"""Regression tests for tests/e2e/helpers (test infrastructure).

BUG-030: ``docker_control.stop/start/restart_container`` returned True on
any subprocess exit code — a failed ``docker stop`` reported success.
BUG-031: ``measure_time`` contextmanager computed ``elapsed`` but never
exposed it — ``with measure_time() as t`` bound ``t`` to ``None``.
BUG-032: ``calculate_percentiles`` used ``int(p*n)`` — off-by-one, so p50
of a 10-sample list returned the 6th element (upper-rank bias).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests" / "e2e"))

import workflow_validator
from helpers import cleanup, docker_control, timing


class TestDockerControlReturnCodes:
    def test_stop_container_returns_false_on_nonzero_exit(self):
        failed = subprocess.CompletedProcess(args=[], returncode=1, stderr="no such container")
        with patch.object(docker_control.subprocess, "run", return_value=failed):
            assert docker_control.stop_container("nonexistent") is False

    def test_start_container_returns_false_on_nonzero_exit(self):
        failed = subprocess.CompletedProcess(args=[], returncode=1, stderr="no such container")
        with patch.object(docker_control.subprocess, "run", return_value=failed):
            assert docker_control.start_container("nonexistent") is False

    def test_restart_container_returns_false_on_nonzero_exit(self):
        failed = subprocess.CompletedProcess(args=[], returncode=1, stderr="daemon error")
        with patch.object(docker_control.subprocess, "run", return_value=failed):
            assert docker_control.restart_container("nonexistent") is False

    def test_stop_container_true_on_success(self):
        ok = subprocess.CompletedProcess(args=[], returncode=0)
        with patch.object(docker_control.subprocess, "run", return_value=ok):
            assert docker_control.stop_container("soar_api") is True


class TestMeasureTime:
    def test_measure_time_exposes_elapsed(self):
        with timing.measure_time() as t:
            pass
        assert isinstance(t, dict)
        assert t["elapsed"] >= 0.0


class TestCalculatePercentiles:
    def test_p50_of_10_samples_is_5th_element(self):
        result = timing.calculate_percentiles(list(range(1, 11)))
        # Canonical algorithm is linear interpolation (domain.statistics):
        # k=(10-1)*0.5=4.5 -> s[4] + 0.5*(s[5]-s[4]) = 5.5
        assert result["p50"] == 5.5

    def test_p90_of_10_samples(self):
        result = timing.calculate_percentiles(list(range(1, 11)))
        # Linear interpolation: k=(10-1)*0.9=8.1 -> s[8] + 0.1*(s[9]-s[8]) = 9.1
        assert result["p90"] == 9.1


class TestWorkflowValidator:
    """BUG-036: `int(http_status)` raised ValueError on non-numeric
    `status` values in a critical node's result (e.g. `{"status": "OK"}`)
    — crashing the validator instead of collecting the error."""

    def _execution(self, result_body: dict) -> dict:
        import json as _json

        return {
            "status": "FINISHED",
            "results": [
                {
                    "action": {"label": "thehive_create_case"},
                    "status": "SUCCESS",
                    "result": _json.dumps(result_body),
                }
            ],
        }

    def test_non_numeric_status_does_not_crash(self):
        execution = self._execution({"status": "OK", "body": {"success": True}})
        # Must not raise — non-numeric status is not an HTTP error.
        assert workflow_validator.validate_workflow_results(execution) is None

    def test_numeric_string_status_still_checked(self):
        execution = self._execution({"status": "500"})
        try:
            workflow_validator.validate_workflow_results(execution)
        except AssertionError as exc:
            assert "HTTP 500" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected AssertionError for HTTP 500")


class TestNoHardcodedCredentials:
    """BUG-037: conftest.py fell back to a hardcoded stale Shuffle API
    key (`c8410826-...`) when SHUFFLE_DEFAULT_APIKEY was unset — silent
    wrong-key auth. Source-level check (conftest monkeypatches sockets
    at import, so it cannot be imported safely)."""

    def test_conftest_has_no_hardcoded_key_fallback(self):
        conftest = (ROOT / "tests" / "e2e" / "conftest.py").read_text(encoding="utf-8")
        assert "c8410826" not in conftest
        import re

        m = re.search(r'os\.environ\.get\("SHUFFLE_DEFAULT_APIKEY",\s*"([^"]*)"\)', conftest)
        assert m is not None
        assert m.group(1) == ""

    def test_service_mixin_has_no_placeholder_key(self):
        mixin = (ROOT / "tests" / "e2e" / "base" / "service_mixins.py").read_text(encoding="utf-8")
        assert '"placeholder"' not in mixin


class TestCleanupHelpers:
    """BUG-039: helpers/cleanup.py repeats the BUG-030 anti-pattern —
    ``docker volume rm`` / ``docker network rm`` return codes are ignored,
    so a failed removal reports success (True)."""

    def _proc(self, rc: int, stdout: str = ""):
        return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout)

    def test_remove_volumes_returns_false_when_rm_fails(self):
        calls = [
            self._proc(0, "soar_data\nsoar_logs"),  # docker volume ls
            self._proc(1, ""),  # rm soar_data fails
            self._proc(0, ""),  # rm soar_logs ok
        ]
        it = iter(calls)
        with patch.object(cleanup.subprocess, "run", side_effect=lambda *a, **k: next(it)):
            assert cleanup.remove_docker_volumes("soar") is False

    def test_remove_networks_returns_false_when_rm_fails(self):
        calls = [
            self._proc(0, "soar_net"),  # docker network ls
            self._proc(1, ""),  # rm fails (in use)
        ]
        it = iter(calls)
        with patch.object(cleanup.subprocess, "run", side_effect=lambda *a, **k: next(it)):
            assert cleanup.remove_docker_networks("soar") is False

    def test_remove_volumes_true_when_all_rm_ok(self):
        calls = [self._proc(0, "soar_a"), self._proc(0, "")]
        it = iter(calls)
        with patch.object(cleanup.subprocess, "run", side_effect=lambda *a, **k: next(it)):
            assert cleanup.remove_docker_volumes("soar") is True


class TestEvidenceComplete:
    """BUG-044: ``assert_evidence_complete`` required ``payload.json``
    unconditionally, but that file is only written by ``submit_alert`` /
    the wrapped webhook POST.  Tests that never submit an alert (e.g.
    TC-10 Tenzir checks) therefore always report FAILED 3/4 in the
    result artifact although pytest itself PASSED — a false negative in
    every generated report/summary."""

    @staticmethod
    def _stub(tmp_path, files, execution_id=None):
        from tests.e2e.base import E2EBaseTest

        evidence = tmp_path / "evidence"
        evidence.mkdir()
        for name in files:
            (evidence / name).write_text("{}", encoding="utf-8")

        class _Stub:
            def __init__(self):
                self.evidence_dir = evidence
                self.execution_id = execution_id
                self.recorded = []

            def record_assertion(self, name, passed, duration, details):
                self.recorded.append((name, passed, details))

            def _log(self, _msg):
                pass

        stub = _Stub()
        E2EBaseTest.assert_evidence_complete(stub)
        return stub

    _ALWAYS = ["service_health.json", "docker_state.json", "workflow_execution.json"]

    def test_non_submitting_test_is_not_failed_for_missing_payload(self, tmp_path):
        stub = self._stub(tmp_path, self._ALWAYS, execution_id=None)
        name, passed, details = stub.recorded[0]
        assert name == "evidence_complete"
        assert details["missing_required"] == []
        assert passed is True

    def test_submitting_test_still_requires_payload(self, tmp_path):
        stub = self._stub(tmp_path, self._ALWAYS, execution_id="exec-1")
        _, passed, details = stub.recorded[0]
        assert "payload.json" in details["missing_required"]
        assert passed is False


class TestConfigProviderEnvFallback:
    """BUG-045: ``InfrastructureConfigProvider.get("UPPERCASE_ENV_VAR")``
    only consulted ``Settings`` attributes and the lowercase ``_config``
    dict — env vars without a dedicated ``@property`` (RATE_LIMIT_*,
    API_REQUIRE_AUTH, INTERNAL_SERVICE_TOKEN…) were silently ignored,
    so e.g. ``RATE_LIMIT_PER_MINUTE=300`` configured 100."""

    def test_env_var_returned_when_no_settings_attr(self, monkeypatch):
        from soar_lab.config.settings import Settings
        from soar_lab.infrastructure.config_provider import (
            InfrastructureConfigProvider,
        )

        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "300")
        cp = InfrastructureConfigProvider(Settings())
        assert cp.get("RATE_LIMIT_PER_MINUTE", 100) == "300"

    def test_settings_attr_still_wins(self, monkeypatch):
        from soar_lab.config.settings import Settings
        from soar_lab.infrastructure.config_provider import (
            InfrastructureConfigProvider,
        )

        monkeypatch.setenv("API_HOST", "9.9.9.9")
        cp = InfrastructureConfigProvider(Settings())
        # API_HOST is a Settings @property — provider must keep using it
        assert cp.get("API_HOST") == "9.9.9.9"


class TestLatencyProbeIsBounded:
    """BUG-046: TC-15 latency tests timed ``thehive.list_cases()`` with the
    default ``range=0-1000``.  With ~640 accumulated cases that call takes
    ~13 s, so GET_SLA (5 s) / P95_SLA (10 s) fail deterministically as the
    case DB grows — the test conflates data volume with API responsiveness.
    The latency probe must use a bounded page (``range_``)."""

    @staticmethod
    def _load_cls():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "test_api_latency",
            ROOT / "tests" / "e2e" / "TC-15" / "test_api_latency.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TestAPILatency

    def _run_get_latency(self):
        from unittest.mock import MagicMock

        cls = self._load_cls()
        stub = cls.__new__(cls)
        stub.thehive = MagicMock()
        stub._measure_latency = lambda func, name: (
            func(),
            {"service": name, "latency_s": 0.001, "latency_ms": 1, "ok": True},
        )[1]
        stub._ensure_workflow_context = lambda: None
        stub._log = lambda *_a, **_k: None
        stub.correlation_id = "x"
        cls.test_get_latency(stub)
        return stub.thehive

    def test_get_latency_probe_uses_bounded_range(self):
        thehive = self._run_get_latency()
        _, kwargs = thehive.list_cases.call_args
        args = thehive.list_cases.call_args[0]
        range_used = kwargs.get("range_", kwargs.get("range", None))
        if range_used is None and args:
            range_used = args[0]
        assert range_used is not None, "list_cases() called unbounded"
        hi = int(str(range_used).split("-")[-1])
        assert hi <= 100, f"probe should page at most 100 cases, got {range_used}"


class TestTC26WebhookSend:
    """BUG-047: TC-26 ``_send_alert_concurrent`` posted with ``timeout=15``
    while the Shuffle webhook persists the execution to OpenSearch
    synchronously — a write that takes ~20-27s under load. Clients hit
    ReadTimeout before the server answered, and definitive 5xx responses
    (write failed, nothing queued — safe to retry) were treated as fatal.
    Observed live: 9x ReadTimeout(15s) + 1x HTTP 500 on a 10-way burst;
    with timeout=60 the single success took 27.3s.

    The sender must outlive the backend write path and retry definitive
    5xx; transport timeouts are NOT retried (the write may have landed
    server-side — a resend would create a duplicate execution)."""

    @staticmethod
    def _load_cls():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "test_extreme_load",
            ROOT / "tests" / "e2e" / "TC-26" / "test_extreme_load.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TestExtremeLoad

    @classmethod
    def _stub(cls):
        from unittest.mock import MagicMock

        klass = cls._load_cls()
        stub = klass.__new__(klass)
        stub.shuffle = MagicMock()
        stub.webhook_url = "https://shuffle-backend:5443/api/v1/hooks/x"
        return stub

    @staticmethod
    def _resp(status, body):
        from unittest.mock import MagicMock

        r = MagicMock()
        r.status_code = status
        r.content = b'{"x":1}'
        r.json.return_value = body
        r.text = str(body)
        return r

    def test_webhook_timeout_covers_backend_write_path(self):
        """timeout must exceed the synchronous OpenSearch write (~20-27s
        under load); 15s produced ReadTimeouts on 9/10 sends."""
        stub = self._stub()
        stub.shuffle._webhook_session.post.return_value = self._resp(200, {"execution_id": "e1"})
        stub._send_alert_concurrent(0, "T")
        timeout = stub.shuffle._webhook_session.post.call_args[1]["timeout"]
        assert timeout >= 45, (
            f"webhook timeout {timeout}s is below the Shuffle->OpenSearch "
            "write path observed at ~20-27s under load — causes ReadTimeout "
            "false negatives (BUG-047)"
        )

    def test_explicit_5xx_is_retried(self):
        """A definitive 5xx means the write failed server-side (nothing
        queued) — retrying is safe and must recover the send."""
        stub = self._stub()
        stub.shuffle._webhook_session.post.side_effect = [
            self._resp(500, {"success": False, "reason": "timeout"}),
            self._resp(500, {"success": False, "reason": "timeout"}),
            self._resp(200, {"execution_id": "e9"}),
        ]
        with patch("time.sleep"):
            res = stub._send_alert_concurrent(0, "T")
        assert res["exec_id"] == "e9", (
            "explicit 5xx must be retried — Shuffle confirmed the write "
            "failed so nothing was queued (BUG-047)"
        )
        assert stub.shuffle._webhook_session.post.call_count == 3

    def test_transport_timeout_is_not_retried(self):
        """A ReadTimeout is ambiguous (the write may have landed) —
        retrying risks a duplicate execution; the send must stay a
        single attempt error."""
        stub = self._stub()
        stub.shuffle._webhook_session.post.side_effect = TimeoutError("read")
        with patch("time.sleep"):
            res = stub._send_alert_concurrent(0, "T")
        assert res["error"] is not None
        assert res["exec_id"] is None
        assert stub.shuffle._webhook_session.post.call_count == 1, (
            "transport timeouts must not be retried — duplicate-execution " "risk (BUG-047)"
        )


class TestKpiAbortExclusionPatterns:
    """BUG-048: ``TC-KPI-06/test_workflow_aborted_rate`` excluía abortos
    intencionales con patrones ``TC-05/TC-19/TC-26/TC-07`` (con guion tras
    TC) — pero todos los ``alert_id`` de la suite usan formato ``TCxx-``
    (``TC26-BACKPRESSURE-*``…). Los patrones eran código muerto: nunca
    casaron → los 42 abortos de TC-26 (techo de ingesta BUG-047) se
    contaron como "inesperados" y el test falló con 7,0 % > 5 %."""

    @staticmethod
    def _load_mod():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "test_service_health",
            ROOT / "tests" / "e2e" / "TC-KPI-06" / "test_service_health.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_tc26_alert_ids_are_excluded(self):
        """Los alert_id reales de TC-26 deben casar los patrones."""
        import fnmatch

        mod = self._load_mod()
        patterns = mod.EXPECTED_ABORT_PATTERNS
        real_ids = [
            "TC26-STORM-1-0",
            "TC26-CONCURRENT-1-5",
            "TC26-BACKPRESSURE-1-7",
            "TC26-DUPLICATE-1",
        ]
        for aid in real_ids:
            assert any(fnmatch.fnmatch(aid, f"*{p}*") for p in patterns), (
                f"alert_id {aid} not covered by EXPECTED_ABORT_PATTERNS " f"{patterns} (BUG-048)"
            )

    def test_every_tc_pattern_matches_a_real_suite_alert_id(self):
        """Cada patrón TC* debe casar al menos un alert_id literal de los
        tests — un patrón que no casa nada es código muerto."""
        import fnmatch
        import re

        mod = self._load_mod()
        tc_patterns = [p for p in mod.EXPECTED_ABORT_PATTERNS if p.startswith("TC")]
        literal_ids = set()
        for f in (ROOT / "tests" / "e2e").rglob("*.py"):
            literal_ids.update(re.findall(r"TC\d{2}-[A-Z0-9_]+", f.read_text(encoding="utf-8")))
        assert literal_ids, "no TCxx alert_ids found in tests/e2e"
        for p in tc_patterns:
            assert any(
                fnmatch.fnmatch(a, f"*{p}*") for a in literal_ids
            ), f"pattern {p} matches no real alert_id — dead pattern (BUG-048)"


class TestKpiAnalyzerMttrBounds:
    """BUG-049: ``kpi_analyzer.calculate_kpis_by_alert_type`` averaged
    ``mttr_seconds`` unbounded — a single corrupt metric doc
    (``detection_time`` in the distant past → mttr 26 609 988 s ≈ 308 días,
    observed live: ransomware avg 47 857 s instead of ~170 s) skewed the
    aggregate by ~280x. Values exceeding the analysis window are
    physically impossible and must be excluded."""

    @staticmethod
    def _calc(metrics, hours=24):
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

        return KPIAnalyzer.calculate_kpis_by_alert_type(metrics, hours)

    def test_outlier_mttr_is_excluded(self):
        """mttr_seconds > window (24h) must not poison the average."""
        metrics = [
            {"alert_type": "ransomware", "mttr_seconds": 170, "severity": 2},
            {"alert_type": "ransomware", "mttr_seconds": 180, "severity": 2},
            {"alert_type": "ransomware", "mttr_seconds": 26_609_988, "severity": 2},
        ]
        out = self._calc(metrics)
        avg = out["by_alert_type"]["ransomware"]["avg_mttr_seconds"]
        assert avg < 1000, (
            f"avg_mttr_seconds {avg} poisoned by a 26.6M-s outlier — "
            "values above the window must be excluded (BUG-049)"
        )

    def test_valid_mttr_values_still_count(self):
        metrics = [
            {"alert_type": "ransomware", "mttr_seconds": 100, "severity": 2},
            {"alert_type": "ransomware", "mttr_seconds": 300, "severity": 2},
        ]
        out = self._calc(metrics)
        assert out["by_alert_type"]["ransomware"]["avg_mttr_seconds"] == 200


class TestDockerProxyImageCoverage:
    """BUG-050: ``docker-compose.hardened.yml`` referenced
    ``tecnativa/docker-socket-proxy:0.4.1`` — the tag does not exist
    (published tags are ``v0.4.x``); ``make up HARDENED=1`` would fail at
    pull time. ``compose config`` cannot catch it (no manifest
    resolution), and ``DOCKER_PROXY_IMAGE`` was missing from
    ``verify_image_digests.py`` coverage — a silent gap.

    Guard: the proxy var must stay in IMAGES so ``make verify-digests``
    (blocking) catches an unresolvable tag."""

    def test_docker_proxy_image_is_digest_verified(self):
        import scripts.maintenance.verify_image_digests as vid

        assert "DOCKER_PROXY_IMAGE" in vid.IMAGES

    def test_hardened_compose_uses_published_tag(self):
        from pathlib import Path

        text = Path("infra/docker/compose/docker-compose.hardened.yml").read_text(encoding="utf-8")
        assert "docker-socket-proxy:0.4.1" not in text
        assert "docker-socket-proxy:v0.4.1" in text


class TestTC26ReconcileUnansweredSends:
    """BUG-051: ``test_alert_storm`` counted a send whose *response* never
    arrived (ReadTimeout / broken response) as error or rejected, while
    Shuffle had already queued the execution server-side — observed
    live: 10/10 STORM executions FINISHED + 10 unique TheHive cases,
    yet pytest FAILED at ``len(accepted) == num_alerts``. Server-side
    state is the ground truth: an existing execution means the alert
    was accepted. ``_reconcile_unanswered_sends`` must reclassify such
    sends before the asserts."""

    @staticmethod
    def _make(executions):
        import importlib.util
        from unittest.mock import MagicMock

        spec = importlib.util.spec_from_file_location(
            "test_extreme_load",
            ROOT / "tests" / "e2e" / "TC-26" / "test_extreme_load.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        inst = mod.TestExtremeLoad.__new__(mod.TestExtremeLoad)
        inst.shuffle = MagicMock()
        inst.shuffle.get_workflow_executions.return_value = executions
        inst.workflow_id = "wf-1"
        inst._log = lambda msg: None
        return inst

    def test_timed_out_send_with_queued_exec_counts_as_accepted(self):
        executions = [
            {"execution_id": "ex-1", "execution_argument": '{"alert_id": "TC26-STORM-1-3"}'}
        ]
        results = [
            {
                "alert_id": "TC26-STORM-1-3",
                "status_code": None,
                "exec_id": None,
                "body": {},
                "error": "ReadTimeout",
            },
        ]
        inst = self._make(executions)
        inst._reconcile_unanswered_sends(results)
        r = results[0]
        assert r["exec_id"] == "ex-1"
        assert r["error"] is None
        assert r["status_code"] == 200

    def test_genuinely_dropped_send_stays_an_error(self):
        results = [
            {
                "alert_id": "TC26-STORM-1-7",
                "status_code": None,
                "exec_id": None,
                "body": {},
                "error": "ReadTimeout",
            },
        ]
        inst = self._make(executions=[])
        inst._reconcile_unanswered_sends(results)
        assert results[0]["error"] == "ReadTimeout"
        assert results[0]["exec_id"] is None


class TestTC26TerminalOutcomeAccounting:
    """BUG-052: ``WORKFLOW_TIMEOUT=600`` sat below the measured burst drain
    (10-burst max 667s — all STORM execs eventually FINISHED) and below
    Shuffle's abort-governor horizon (~1300s): ``test_alert_storm`` failed
    ``len(finished)==num_alerts`` on execs still in-flight at deadline,
    and ``test_backpressure`` demanded all-FINISHED while the system
    sheds overload explicitly via ABORTED. The honest invariant: every
    accepted exec reaches a terminal, auditable state — no silent loss.
    """

    @staticmethod
    def _cls():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "test_extreme_load",
            ROOT / "tests" / "e2e" / "TC-26" / "test_extreme_load.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.TestExtremeLoad

    def test_aborted_counts_as_terminal_not_silent_loss(self):
        inst = self._cls().__new__(self._cls())
        ids = ["a", "b", "c"]
        results = {
            "a": {"status": "FINISHED"},
            "b": {"status": "ABORTED"},
            "c": {"status": "FAILED"},
        }
        finished, terminal, unaccounted = inst._classify_exec_outcomes(ids, results)
        assert finished == ["a"]
        assert set(terminal) == {"a", "b", "c"}
        assert unaccounted == [], (
            "ABORTED/FAILED are auditable outcomes — only missing/executing "
            "execs are silent loss (BUG-052)"
        )

    def test_still_executing_counts_as_unaccounted(self):
        inst = self._cls().__new__(self._cls())
        ids = ["a", "b"]
        results = {"a": {"status": "FINISHED"}, "b": {"status": "TIMEOUT"}}
        _, terminal, unaccounted = inst._classify_exec_outcomes(ids, results)
        assert unaccounted == ["b"]

    def test_wait_windows_cover_measured_horizons(self):
        cls = self._cls()
        assert cls.STORM_WAIT_TIMEOUT > 600
        assert cls.BACKPRESSURE_WAIT_TIMEOUT >= 1500


class TestTC26FinalStatusRecheck:
    """BUG-052 (cont.): execs still EXECUTING when the terminal wait
    expires are not silent loss — the abort governor reaps them ~4-10 min
    past the window (verified live: the 9 TIMEOUT execs turned ABORTED
    after deadline). ``_final_status_recheck`` must distinguish:
    terminal-now → accounted; EXECUTING fresh → tracked in-flight;
    missing or EXECUTING stale (>2× observed max duration) → real loss."""

    @staticmethod
    def _make(execution):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "test_extreme_load",
            ROOT / "tests" / "e2e" / "TC-26" / "test_extreme_load.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        inst = mod.TestExtremeLoad.__new__(mod.TestExtremeLoad)
        inst._get_execution = lambda eid: execution
        return inst

    def test_terminal_now_counts(self):
        inst = self._make({"status": "ABORTED", "started_at": 1})
        assert inst._final_status_recheck("x") == "terminal"

    def test_fresh_executing_is_in_flight(self):
        import time

        inst = self._make({"status": "EXECUTING", "started_at": time.time() - 300})
        assert inst._final_status_recheck("x") == "in-flight"

    def test_stale_executing_is_lost(self):
        import time

        inst = self._make({"status": "EXECUTING", "started_at": time.time() - 9999})
        assert inst._final_status_recheck("x") == "lost"

    def test_missing_is_lost(self):
        inst = self._make(None)
        assert inst._final_status_recheck("x") == "lost"
