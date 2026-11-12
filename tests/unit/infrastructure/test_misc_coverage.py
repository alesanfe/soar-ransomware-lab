#!/usr/bin/env python3
"""Targeted coverage: mitre schema, severity, worker_lease, clients factories."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

# ---------- config/schemas/mitre.py ----------


class TestMitreSchema:
    def test_dict_technique_ok(self):
        from soar_lab.config.schemas.mitre import MITREInfo

        m = MITREInfo(techniques=[{"id": "T1486", "name": "Data Encrypted"}])
        assert m.techniques[0]["id"] == "T1486"

    def test_dict_technique_bad_id(self):
        from soar_lab.config.schemas.mitre import MITREInfo

        with pytest.raises(Exception, match="Invalid MITRE technique"):
            MITREInfo(techniques=[{"id": "bogus"}])

    def test_str_technique_bad(self):
        from soar_lab.config.schemas.mitre import MITREInfo

        with pytest.raises(Exception, match="Invalid MITRE technique"):
            MITREInfo(techniques=["not-a-technique"])

    def test_non_str_non_dict_rejected(self):
        from soar_lab.config.schemas.mitre import MITREInfo

        with pytest.raises(Exception, match="must be string or dict"):
            MITREInfo(techniques=[42])

    def test_sub_technique_pattern_ok(self):
        from soar_lab.config.schemas.mitre import MITREInfo

        assert MITREInfo(techniques=["T1003.001"]).techniques == ["T1003.001"]


# ---------- domain/severity.py ----------


class TestSeverityContract:
    def test_none_raises(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="^severity is required$"):
            normalize_severity(None)

    def test_bool_raises(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="^severity must not be a bool$"):
            normalize_severity(True)

    def test_int_out_of_range_raises(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="^severity int must be in 0..4$"):
            normalize_severity(5)

    def test_float_integral_ok(self):
        from soar_lab.domain.severity import normalize_severity

        assert normalize_severity(3.0) == 3

    def test_float_nonintegral_raises(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="integral"):
            normalize_severity(2.5)

    def test_float_at_boundaries(self):
        """Integral floats AT the range bounds must normalize — a `<` vs
        `<=` slip in the float branch would silently reject severity=4.0."""
        from soar_lab.domain.severity import normalize_severity

        assert normalize_severity(0.0) == 0
        assert normalize_severity(4.0) == 4

    def test_named_and_numeric_strings(self):
        from soar_lab.domain.severity import normalize_severity

        assert normalize_severity(" High ") == 3
        assert normalize_severity("2.0") == 2

    def test_empty_and_unknown_str(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="^severity must not be empty$"):
            normalize_severity("   ")
        with pytest.raises(SeverityContractError, match="^unknown severity name: 'apocalyptic'$"):
            normalize_severity("apocalyptic")

    def test_disallowed_type(self):
        from soar_lab.domain.severity import SeverityContractError, normalize_severity

        with pytest.raises(SeverityContractError, match="^severity type not allowed: list$"):
            normalize_severity([1])

    def test_to_thehive_mapping(self):
        from soar_lab.domain.severity import severity_to_thehive

        assert severity_to_thehive(0) == 1
        assert severity_to_thehive(2) == 2
        assert severity_to_thehive(4) == 3


# ---------- domain/models.py ----------


class TestCaseFromDict:
    def test_default_created_at_is_tz_aware(self):
        """When `created_at` is absent, the default must be a timezone-
        aware UTC datetime — a naive `datetime.now()` leaks local time
        into serialized ISO strings."""
        from soar_lab.domain.models import Case

        case = Case.from_dict(
            {
                "case_id": "c1",
                "title": "t",
                "description": "d",
                "severity": 2,
                "status": "new",
            }
        )
        assert case.created_at.tzinfo is not None
        assert case.created_at.utcoffset() is not None


# ---------- infrastructure/messaging/worker_lease.py ----------


class TestWorkerLease:
    def _lease(self, client):
        from soar_lab.infrastructure.messaging.worker_lease import WorkerLease

        return WorkerLease(client, holder="w1", ttl_ms=1000)

    async def test_eval_exception_returns_false(self):
        c = AsyncMock()
        c.eval.side_effect = RuntimeError("redis down")
        assert await self._lease(c).held() is False

    async def test_other_holder_returns_false(self):
        c = AsyncMock()
        c.eval.return_value = 0
        assert await self._lease(c).held() is False

    async def test_fresh_acquire_fences(self):
        c = AsyncMock()
        c.eval.return_value = 2
        c.incr.return_value = 7
        lease = self._lease(c)
        assert await lease.held() is True
        assert lease.fence_token == 7

    async def test_fence_incr_failure_leaves_none(self):
        c = AsyncMock()
        c.eval.return_value = 2
        c.incr.side_effect = RuntimeError("boom")
        lease = self._lease(c)
        assert await lease.held() is True
        assert lease.fence_token is None

    async def test_renew_own_returns_true_no_fence(self):
        c = AsyncMock()
        c.eval.return_value = 1
        lease = self._lease(c)
        assert await lease.held() is True
        c.incr.assert_not_awaited()

    async def test_release_calls_script_and_swallows_errors(self):
        c = AsyncMock()
        lease = self._lease(c)
        await lease.release()
        c.eval.assert_awaited_once()
        c.eval.side_effect = RuntimeError("gone")
        await lease.release()  # must not raise

    async def test_no_client_release_noop(self):
        assert await self._lease(None).held() is True
        await self._lease(None).release()


# ---------- infrastructure/clients.py ----------


class TestClientFactories:
    def test_gateway_strategy_success(self):
        from soar_lab.infrastructure.clients import GatewayIPStrategy

        with patch("soar_lab.infrastructure.clients.docker.DockerClient") as dc:
            assert GatewayIPStrategy("1.2.3.4").connect("/sock") is dc.return_value
            dc.assert_called_once_with(base_url="tcp://1.2.3.4:2375", version="auto")

    def test_unix_strategy_success(self):
        from soar_lab.infrastructure.clients import UnixSocketStrategy

        with patch("soar_lab.infrastructure.clients.docker.DockerClient") as dc:
            assert UnixSocketStrategy().connect("/var/run/d.sock") is dc.return_value

    def test_env_strategy_success(self):
        from soar_lab.infrastructure.clients import DefaultFromEnvStrategy

        with patch("soar_lab.infrastructure.clients.docker.from_env") as fe:
            assert DefaultFromEnvStrategy().connect("/x") is fe.return_value

    def test_redis_success_and_missing_url(self):
        from soar_lab.infrastructure.clients import create_redis_client

        cp = Mock()
        cp.get.return_value = "redis://x:6379"
        with patch("soar_lab.infrastructure.clients.redis.from_url") as fu:
            assert create_redis_client(cp) is fu.return_value
        cp.get.return_value = None
        assert create_redis_client(cp) is None

    async def test_async_redis_paths(self):
        from soar_lab.infrastructure.clients import create_async_redis_client

        cp = Mock()
        cp.get.return_value = None
        assert await create_async_redis_client(cp) is None

        cp.get.return_value = "redis://x:6379"
        good = AsyncMock()
        with patch(
            "soar_lab.infrastructure.clients.redis.asyncio.from_url", return_value=good
        ) as fu:
            assert await create_async_redis_client(cp) is good
            good.ping.assert_awaited_once()

        fu.side_effect = RuntimeError("down")
        assert await create_async_redis_client(cp) is None

    def test_docker_client_all_strategies_fail(self):
        from soar_lab.infrastructure.clients import create_docker_client

        cp = Mock()
        cp.get.side_effect = lambda k, d=None: {"docker_gateway_ip": "9.9.9.9"}.get(k, d)
        with (
            patch("soar_lab.infrastructure.clients.docker.DockerClient", side_effect=RuntimeError),
            patch("soar_lab.infrastructure.clients.docker.from_env", side_effect=RuntimeError),
        ):
            assert create_docker_client(cp) is None
