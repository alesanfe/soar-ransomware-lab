#!/usr/bin/env python3
"""Coverage for interfaces/api/auth.py internal helpers."""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from soar_lab.interfaces.api import auth as A


def _req(path="/x", method="GET", headers=None, client_host="10.0.0.1", **state):
    r = Mock()
    r.url.path = path
    r.method = method
    r.headers = headers or {}
    r.client = Mock(host=client_host) if client_host else None
    r.app.state = Mock(**state)
    r.state = Mock()
    return r


def _cp(values):
    cp = Mock()
    cp.get = Mock(side_effect=lambda k, d=None: values.get(k, d))
    return cp


class TestScopeAllowed:
    def test_unknown_scope_denies(self):
        assert A._scope_allowed("bogus", "GET", "/x") is False

    def test_empty_rules_allows_everything(self):
        assert A._scope_allowed("internal", "DELETE", "/anything") is True

    def test_exact_and_prefix_matching(self):
        assert A._scope_allowed("webhook", "POST", "/api/v1/alerts") is True
        assert A._scope_allowed("webhook", "GET", "/api/v1/alerts") is False
        assert A._scope_allowed("webhook", "POST", "/api/v1/alerts/callback") is False


class TestServiceTokenScope:
    def test_no_token_returns_none(self):
        scope, grace, fp = A._service_token_scope(_req(), _cp({}))
        assert (scope, grace, fp) == (None, False, None)

    def test_authorization_scheme_fallback(self):
        cp = _cp({"INTERNAL_SERVICE_TOKEN": "tok-1"})
        r = _req(headers={"Authorization": "Service-Token tok-1"})
        scope, grace, fp = A._service_token_scope(r, cp)
        assert scope == "internal" and grace is False and fp

    def test_prev_token_grants_rotation_grace(self):
        cp = _cp({"SHUFFLE_WEBHOOK_TOKEN_PREV": "old-tok"})
        r = _req(headers={"X-Service-Token": "old-tok"})
        scope, grace, _ = A._service_token_scope(r, cp)
        assert scope == "webhook" and grace is True

    def test_wrong_token_none(self):
        cp = _cp({"INTERNAL_SERVICE_TOKEN": "right"})
        r = _req(headers={"X-Service-Token": "wrong"})
        assert A._service_token_scope(r, cp) == (None, False, None)


class TestCidrAllowlist:
    def test_empty_allows(self):
        assert A._webhook_cidr_allowed(_req(), _cp({})) is True

    def test_no_client_denies(self):
        r = _req(client_host=None)
        assert A._webhook_cidr_allowed(r, _cp({"WEBHOOK_ALLOW_CIDRS": "10.0.0.0/8"})) is False

    def test_ip_in_cidr_and_bad_entries_ignored(self):
        cp = _cp({"WEBHOOK_ALLOW_CIDRS": "bogus, 10.0.0.0/8,172.16.0.0/12"})
        assert A._webhook_cidr_allowed(_req(client_host="10.1.2.3"), cp) is True
        assert A._webhook_cidr_allowed(_req(client_host="192.168.1.1"), cp) is False


class TestServiceTokenPrincipal:
    def _req(self):
        return _req(auth_service=Mock(audit=Mock()))

    def test_cidr_blocked_403_and_audited(self):
        r = self._req()
        cp = _cp({"WEBHOOK_ALLOW_CIDRS": "10.0.0.0/8"})
        r.client.host = "192.168.1.1"
        with pytest.raises(HTTPException) as e:
            A._service_token_principal(r, cp, "webhook", False)
        assert e.value.status_code == 403
        assert r.app.state.auth_service.audit.record.called

    def test_scope_denied_403(self):
        r = self._req()
        with pytest.raises(HTTPException) as e:
            A._service_token_principal(r, _cp({}), "webhook", False)
        assert e.value.status_code == 403

    def test_rotation_grace_warns_and_allows(self):
        r = self._req()
        p = A._service_token_principal(r, _cp({}), "internal", True, "fp12")
        assert p == {"service": "internal", "credential_id": "fp12"}
        assert r.state._auth_principal == p


class TestAuditAccess:
    def test_no_auth_service_or_audit_noop(self):
        A._audit_access(_req(), principal="a", result="deny")
        r = _req()
        r.app.state.auth_service = None
        A._audit_access(r, principal="a", result="deny")

    def test_record_exception_swallowed(self):
        audit = Mock()
        audit.record.side_effect = RuntimeError("x")
        r = _req(auth_service=Mock(audit=audit))
        A._audit_access(r, principal="a", result="deny")  # no raise


class TestJwtPrincipal:
    def test_no_get_current_user_returns_none(self):
        r = _req()
        r.app.state.get_current_user = None
        assert A._jwt_principal(r, Mock()) is None

    def test_invalid_jwt_audited_and_reraises(self):
        r = _req()

        def deny(creds):
            raise HTTPException(status_code=401)

        r.app.state.get_current_user = deny
        r.app.state.auth_service = Mock(audit=Mock())
        with pytest.raises(HTTPException):
            A._jwt_principal(r, Mock())
        assert r.app.state.auth_service.audit.record.called
