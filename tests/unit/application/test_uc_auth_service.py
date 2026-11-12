#!/usr/bin/env python3
"""Unit tests for application/use_cases/auth_service.py — RBAC + audit chain."""

import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from soar_lab.application.use_cases.auth_service import (
    AuthService,
    PermissionGrant,
    set_default_factories,
)
from soar_lab.auth.models import Permission, Role


def _svc(cp=None, tp=None):
    return AuthService(
        config_provider=cp or Mock(get=Mock(return_value=None)),
        token_provider=tp or Mock(),
    )


def _user(role=Role.ANALYST, perms=(), temp=()):
    return SimpleNamespace(
        role=role, permissions=list(perms), temp_permissions=list(temp), username="u"
    )


class TestFactories:
    def test_none_providers_rejected(self):
        with pytest.raises(ValueError, match="config_provider"):
            AuthService(config_provider=None, token_provider=Mock())
        with pytest.raises(ValueError, match="token_provider"):
            AuthService(config_provider=Mock(), token_provider=None)

    def test_default_factories(self):
        set_default_factories(config_factory=lambda: Mock(), token_factory=lambda: Mock())
        svc = AuthService()  # both ellipsis -> factories
        assert svc.config_provider is not None and svc.token_provider is not None


class TestAuditChain:
    def test_record_trim_chain_tip_and_verify(self):
        svc = _svc()
        svc.audit._max = 5
        for i in range(8):
            svc.audit.record("act", i=i)
        assert len(svc.audit.events) == 5
        assert svc.audit.verify() is True
        assert svc.audit.chain_tip == svc.audit.events[-1]["hash"]

    def test_verify_detects_tamper(self):
        svc = _svc()
        svc.audit.record("a")
        svc.audit.record("b")
        svc.audit.events[0]["action"] = "forged"
        assert svc.audit.verify() is False
        # broken prev_hash link also detected
        svc2 = _svc()
        svc2.audit.record("a")
        svc2.audit.record("b")
        svc2.audit.events[1]["prev_hash"] = "0" * 64
        assert svc2.audit.verify() is False
        # empty trail verifies
        assert _svc().audit.verify() is True


class TestRbac:
    def test_admin_shortcuts(self):
        svc = _svc()
        assert svc.has_permission(_user(Role.ADMIN), Permission.DELETE_CASES) is True
        svc.check_permission(_user(Role.ADMIN), Permission.ALL)  # no raise

    def test_permission_and_temp_grant(self):
        svc = _svc()
        u = _user(perms=[Permission.READ_ALERTS])
        assert svc.has_permission(u, Permission.READ_ALERTS)
        with pytest.raises(PermissionError):
            svc.check_permission(u, Permission.DELETE_CASES)

        expired = PermissionGrant(Permission.DELETE_CASES, 0, time.time() - 1)
        live = PermissionGrant(Permission.DELETE_CASES, 0, time.time() + 60)
        u.temp_permissions = [expired, live]
        assert svc.has_permission(u, Permission.DELETE_CASES)
        assert u.temp_permissions == [live]  # expired pruned

    def test_grant_revoke_by_admin_only(self):
        svc = _svc()
        u, admin = _user(), _user(Role.ADMIN)
        with pytest.raises(PermissionError):
            svc.grant_permission(u, Permission.MANAGE_USERS, admin_user=u)
        svc.grant_permission(u, Permission.MANAGE_USERS, admin_user=admin)
        assert Permission.MANAGE_USERS in u.permissions
        svc.revoke_permission(u, Permission.MANAGE_USERS)
        assert Permission.MANAGE_USERS not in u.permissions
        svc.revoke_permission(u, Permission.MANAGE_USERS)  # idempotent

    def test_grant_temporary(self):
        svc = _svc()
        u, admin = _user(), _user(Role.ADMIN)
        with pytest.raises(PermissionError):
            svc.grant_temporary_permission(u, Permission.ALL, admin_user=u)
        g = svc.grant_temporary_permission(u, Permission.ALL, admin_user=admin, duration_seconds=30)
        assert g.expires_at > time.time()
        assert svc.has_permission(u, Permission.ALL)

    def test_role_permissions_matrix(self):
        svc = _svc()
        assert svc.get_role_permissions(Role.ADMIN) == list(Permission)
        assert Permission.UPDATE_CASES in svc.get_role_permissions(Role.OPERATOR)
        analyst = svc.get_role_permissions(Role.ANALYST)
        assert Permission.UPDATE_CASES not in analyst
        assert svc.get_role_permissions(Role.VIEWER) == [
            Permission.READ_ALERTS,
            Permission.READ_CASES,
        ]
        assert svc.get_role_permissions(Role.READONLY) == [
            Permission.READ_ALERTS,
            Permission.READ_CASES,
        ]
        assert svc.get_role_permissions(object()) == []


class TestEndpointAccess:
    def test_admin_and_admin_prefixes(self):
        svc = _svc()
        assert svc.can_access_endpoint(_user(Role.ADMIN), "/backup", "POST") is True
        assert svc.can_access_endpoint(_user(Role.OPERATOR), "/backup", "POST") is False
        assert svc.can_access_endpoint(_user(Role.ANALYST), "/api/v1/audit", "GET") is False

    def test_auth_bootstrap_any_role(self):
        svc = _svc()
        assert svc.can_access_endpoint(_user(Role.VIEWER), "/auth/verify", "GET") is True

    def test_operator_prefixes(self):
        svc = _svc()
        assert svc.can_access_endpoint(_user(Role.OPERATOR), "/api/v1/contain/x", "POST") is True
        assert svc.can_access_endpoint(_user(Role.ANALYST), "/api/v1/contain/x", "POST") is False

    def test_get_read_roles_and_permission_path(self):
        svc = _svc()
        assert svc.can_access_endpoint(_user(Role.VIEWER), "/x", "GET") is True
        assert svc.can_access_endpoint(_user(Role.OPERATOR), "/x", "GET") is True
        u = _user(role=None, perms=[Permission.READ_ALERTS])
        assert svc.can_access_endpoint(u, "/x", "GET") is True

    def test_analyst_post_prefixes_and_create_cases(self):
        svc = _svc()
        assert svc.can_access_endpoint(_user(Role.ANALYST), "/api/v1/alerts", "POST") is True
        assert svc.can_access_endpoint(_user(Role.VIEWER), "/api/v1/alerts", "POST") is False
        u = _user(role=None, perms=[Permission.CREATE_CASES])
        assert svc.can_access_endpoint(u, "/anywhere", "POST") is True
        assert svc.can_access_endpoint(_user(role=None), "/anywhere", "POST") is False


class TestCredentialsAndJwt:
    def _cp(self, values):
        cp = Mock()
        cp.get = Mock(side_effect=lambda k, d=None: values.get(k, d))
        return cp

    def test_verify_credentials_variants(self):
        cp = self._cp({})
        assert _svc(cp=cp).verify_credentials("u", "p") is False  # unset

        cp = self._cp({"web_ui_user": "admin", "web_ui_password": "s3cret"})
        svc = _svc(cp=cp)
        assert svc.verify_credentials("admin", "s3cret") is True
        assert svc.verify_credentials("admin", "wrong") is False
        assert svc.verify_credentials("other", "s3cret") is False

    def test_create_jwt_token_paths(self):
        from soar_lab.common.exceptions import AuthError

        svc = _svc(cp=self._cp({}))
        with pytest.raises(AuthError):  # no secret at all
            svc.create_jwt_token("u")

        cp = self._cp({"jwt_secret_key": "short"})
        with pytest.raises(AuthError):  # SEC-001: <32 rejected
            _svc(cp=cp).create_jwt_token("u")

        cp = self._cp({"jwt_secret_key": "x" * 32, "WEB_UI_ROLE": "analyst"})
        tp = Mock()
        tp.create_token.return_value = "tok"
        svc = _svc(cp=cp, tp=tp)
        assert svc.create_jwt_token("u") == "tok"
        assert tp.create_token.call_args.kwargs["extra_claims"] == {"role": "analyst"}

    def test_verify_jwt_token_paths(self):
        from soar_lab.common.exceptions import AuthError

        with pytest.raises(AuthError):
            _svc(cp=self._cp({})).verify_jwt_token("t")

        cp = self._cp({"api_auth_secret": "y" * 32})
        tp = Mock()
        tp.verify_token.return_value = {"user": "u"}
        assert _svc(cp=cp, tp=tp).verify_jwt_token("t") == {"user": "u"}
