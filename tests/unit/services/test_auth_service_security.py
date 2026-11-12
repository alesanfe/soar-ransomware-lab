#!/usr/bin/env python3
"""SEC-001/002/003 + RES-001/002/003/004 security & resilience tests."""

import time
from unittest.mock import Mock

import pytest

from soar_lab.application.use_cases.auth_service import AuthService
from soar_lab.auth.models import Permission, Role, User
from soar_lab.common.exceptions import AuthError
from soar_lab.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitOpenError,
)


def _service(config_vals=None):
    cfg = Mock()
    vals = config_vals or {}
    cfg.get.side_effect = lambda k, d=None: vals.get(k, d)
    return AuthService(cfg, Mock())


class TestSecretLengthBypass:
    """SEC-001: api_auth_secret must not bypass the 32-char minimum."""

    @pytest.mark.parametrize("secret", ["short", "x" * 31, ""])
    def test_effective_secret_enforced_with_api_secret_set(self, secret):
        svc = _service({"api_auth_secret": secret})
        with pytest.raises(AuthError):
            svc._validate_secret_length(secret)

    def test_long_api_secret_passes(self):
        svc = _service({"api_auth_secret": "x" * 40})
        assert svc._validate_secret_length("x" * 40) is None

    def test_jwt_secret_still_enforced(self):
        svc = _service({"jwt_secret_key": "y" * 40})
        svc._validate_secret_length("y" * 40)
        with pytest.raises(AuthError):
            svc._validate_secret_length("y" * 10)


class TestTemporaryPermissions:
    """SEC-002/003: real expiry + admin-only grants."""

    def test_self_grant_rejected(self):
        svc = _service()
        user = User(username="analyst", role=Role.ANALYST)
        with pytest.raises(PermissionError):
            svc.grant_temporary_permission(user, Permission.DELETE_CASES)

    def test_admin_grant_expires(self):
        svc = _service()
        admin = User(username="root", role=Role.ADMIN)
        user = User(username="analyst", role=Role.ANALYST)
        assert not svc.has_permission(user, Permission.DELETE_CASES)

        svc.grant_temporary_permission(
            user, Permission.DELETE_CASES, admin_user=admin, duration_seconds=3600
        )
        assert svc.has_permission(user, Permission.DELETE_CASES)

    def test_expired_grant_denies(self):
        svc = _service()
        admin = User(username="root", role=Role.ADMIN)
        user = User(username="analyst", role=Role.ANALYST)
        svc.grant_temporary_permission(
            user, Permission.DELETE_CASES, admin_user=admin, duration_seconds=-1
        )
        assert not svc.has_permission(user, Permission.DELETE_CASES)

    def test_expired_grants_pruned(self):
        svc = _service()
        admin = User(username="root", role=Role.ADMIN)
        user = User(username="a", role=Role.ANALYST)
        svc.grant_temporary_permission(
            user, Permission.DELETE_CASES, admin_user=admin, duration_seconds=-1
        )
        svc.has_permission(user, Permission.DELETE_CASES)
        assert user.temp_permissions == []

    def test_grant_audited(self):
        svc = _service()
        admin = User(username="root", role=Role.ADMIN)
        user = User(username="a", role=Role.ANALYST)
        svc.grant_temporary_permission(user, Permission.READ_CASES, admin_user=admin)
        actions = [e["action"] for e in svc.audit.events]
        assert "grant" in actions

    def test_permanent_permissions_unaffected(self):
        svc = _service()
        user = User(username="a", role=Role.ANALYST, permissions=[Permission.READ_ALERTS])
        assert svc.has_permission(user, Permission.READ_ALERTS)


class TestCircuitBreakerResilience:
    def test_open_raises_typed_error_not_bare_exception(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("boom")))
        assert cb.state == CircuitBreakerState.OPEN
        with pytest.raises(CircuitOpenError):
            cb.call(lambda: 1)

    def test_circuit_open_error_not_retryable(self):
        err = CircuitOpenError()
        assert err.retryable is False

    def test_half_open_probe_limit(self):
        # expected_exception=ValueError so probe RuntimeErrors are
        # out-of-contract exceptions (raise, but don't count as failures).
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0,
            expected_exception=ValueError,
            max_probe_requests=2,
        )
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("boom")))
        assert cb.state == CircuitBreakerState.OPEN

        calls = []

        def probe_ok():
            calls.append(1)
            raise RuntimeError("not-expected-exception")  # not counted

        time.sleep(0.01)
        cb.attempt_reset()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        # 2 probes admitted (RuntimeError isn't expected_exception → the
        # call raises but doesn't reopen the breaker)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(probe_ok)
        assert len(calls) == 2
        # 3rd probe rejected WITHOUT calling func — probe limit (RES-003)
        with pytest.raises(CircuitOpenError):
            cb.call(probe_ok)
        assert len(calls) == 2

    def test_context_manager_matches_call_semantics(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("boom")))
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.01)
        with cb:  # transitions OPEN→HALF_OPEN like call() does
            pass
        assert cb.state == CircuitBreakerState.CLOSED
