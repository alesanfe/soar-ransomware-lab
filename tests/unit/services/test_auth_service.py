#!/usr/bin/env python3
"""Unit tests for auth_service.py Tests authentication service with mocked
dependencies."""

from unittest.mock import Mock

import pytest

import soar_lab.application.use_cases.auth_service as auth_mod
from soar_lab.application.use_cases.auth_service import AuthService, _AuthAudit
from soar_lab.auth.models import Permission, Role, User
from soar_lab.common.exceptions import AuthError


class TestAuthService:
    """Test AuthService."""

    def test_initialization_success(self):
        """Test successful initialization."""
        mock_config = Mock()
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        assert service.config_provider == mock_config
        assert service.token_provider == mock_token_provider

    def test_requires_config_provider(self):
        """Test that config_provider is required."""
        mock_token_provider = Mock()
        with pytest.raises(ValueError, match="config_provider is required"):
            AuthService(None, mock_token_provider)

    def test_requires_token_provider(self):
        """Test that token_provider is required."""
        mock_config = Mock()
        with pytest.raises(ValueError, match="token_provider is required"):
            AuthService(mock_config, None)

    def test_verify_credentials_success(self):
        """Test successful credential verification."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "web_ui_user": "admin",
            "web_ui_password": "password",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")

        assert result is True

    def test_verify_credentials_failure(self):
        """Test failed credential verification."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "web_ui_user": "admin",
            "web_ui_password": "password",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "wrong")

        assert result is False

    def test_verify_credentials_not_configured(self):
        """Test credential verification when not configured."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        result = service.verify_credentials("admin", "password")

        assert result is False

    def test_create_jwt_token_success(self):
        """Test successful JWT token creation."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "test-secret-key-min-32-chars-long",
            "api_auth_secret": "",
            "JWT_EXPIRATION_MINUTES": 60,
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.create_token.return_value = "test-token"

        service = AuthService(mock_config, mock_token_provider)
        token = service.create_jwt_token("testuser")

        assert token == "test-token"
        mock_token_provider.create_token.assert_called_once_with(
            "testuser",
            "test-secret-key-min-32-chars-long",
            60,
            "HS256",
            extra_claims={"role": "admin"},
        )

    def test_create_jwt_token_no_secret(self):
        """Test JWT token creation when secret is not configured."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.create_jwt_token("testuser")

    def test_create_jwt_token_short_secret(self):
        """Test JWT token creation with short secret (non-legacy)"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "short",
            "api_auth_secret": "",
            "JWT_EXPIRATION_MINUTES": 60,
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.create_jwt_token("testuser")

    def test_create_jwt_token_short_secret_legacy(self):
        """SEC-001 regression: legacy API_AUTH_SECRET no longer bypasses
        the 32-char minimum — the effective secret must always qualify."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "short",
            "api_auth_secret": "legacy-secret",
            "JWT_EXPIRATION_MINUTES": 60,
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        with pytest.raises(AuthError):
            service.create_jwt_token("testuser")

    def test_verify_jwt_token_success(self):
        """Test successful JWT token verification."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "test-secret-key-min-32-chars-long",
            "api_auth_secret": "",
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()
        mock_token_provider.verify_token.return_value = {"user": "testuser", "method": "jwt"}

        service = AuthService(mock_config, mock_token_provider)
        payload = service.verify_jwt_token("test-token")

        assert payload == {"user": "testuser", "method": "jwt"}
        mock_token_provider.verify_token.assert_called_once_with(
            "test-token", "test-secret-key-min-32-chars-long", "HS256"
        )

    def test_verify_jwt_token_no_secret(self):
        """Test JWT token verification when secret is not configured."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.verify_jwt_token("test-token")

    def test_verify_jwt_token_short_secret(self):
        """Test JWT token verification with short secret (non-legacy)"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "short",
            "api_auth_secret": "",
            "JWT_ALGORITHM": "HS256",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)

        with pytest.raises(AuthError, match="Authentication system not properly configured"):
            service.verify_jwt_token("test-token")

    def test_get_auth_secret_uses_jwt_secret(self):
        """Test _get_auth_secret uses jwt_secret_key."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": "jwt-secret",
            "api_auth_secret": "api-secret",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == "jwt-secret"

    def test_get_auth_secret_fallback_to_api_auth(self):
        """Test _get_auth_secret falls back to api_auth_secret."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "jwt_secret_key": None,
            "api_auth_secret": "api-secret",
        }.get(key, default)
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == "api-secret"

    def test_get_auth_secret_empty_when_none(self):
        """Test _get_auth_secret returns empty string when neither is set."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: None
        mock_token_provider = Mock()

        service = AuthService(mock_config, mock_token_provider)
        secret = service._get_auth_secret()

        assert secret == ""


def test_verify_credentials_uses_constant_time_comparison():
    """Bug: == comparison leaks timing side-channel (CWE-208). Credential
    checks must go through hmac.compare_digest."""
    import hmac as _hmac
    from unittest.mock import patch

    from soar_lab.application.use_cases.auth_service import AuthService

    svc = AuthService(
        config_provider=type(
            "CP",
            (),
            {
                "get": lambda s, k, d=None: {"web_ui_user": "admin", "web_ui_password": "pw"}.get(
                    k, d
                )
            },
        )(),
        token_provider=object(),
    )
    calls = []
    real = _hmac.compare_digest
    with patch(
        "hmac.compare_digest", side_effect=lambda a, b: (calls.append((a, b)), real(a, b))[1]
    ):
        assert svc.verify_credentials("admin", "pw") is True
    assert ("admin", "admin") in calls or b"admin" in [c[0] for c in calls]
    assert ("pw", "pw") in calls or b"pw" in [c[0] for c in calls]


class TestAuthAudit:
    """_AuthAudit hash-chained trail (SEC-006-lite)."""

    def test_record_advances_chain_tip(self):
        audit = _AuthAudit()
        tip0 = audit.chain_tip
        audit.record("grant", user="u")
        assert audit.chain_tip != tip0
        assert len(audit.events) == 1
        assert audit.events[0]["prev_hash"] == tip0

    def test_verify_clean_chain(self):
        audit = _AuthAudit()
        for i in range(5):
            audit.record("evt", n=i)
        assert audit.verify() is True

    def test_verify_detects_tamper(self):
        audit = _AuthAudit()
        for i in range(3):
            audit.record("evt", n=i)
        audit.events[1]["action"] = "forged"
        assert audit.verify() is False

    def test_verify_broken_prev_link(self):
        audit = _AuthAudit()
        for i in range(3):
            audit.record("evt", n=i)
        audit.events[1]["prev_hash"] = "0" * 64
        assert audit.verify() is False

    def test_trim_keeps_verifiable_tail(self):
        audit = _AuthAudit(_max=5)
        for i in range(8):
            audit.record("evt", n=i)
        assert len(audit.events) == 5
        assert audit.verify() is True
        assert audit.events[0]["n"] == 3

    def test_verify_empty(self):
        assert _AuthAudit().verify() is True


class TestDefaultFactories:
    """set_default_factories / ellipsis-init resolution."""

    def _svc(self, **kw):
        return AuthService(**kw)

    def test_only_config_factory_registered(self):
        sentinel = object()
        old_cfg, old_tok = auth_mod._default_config_factory, auth_mod._default_token_factory
        try:
            auth_mod.set_default_factories(config_factory=lambda: sentinel)
            assert auth_mod._default_config_factory is not None
            assert auth_mod._default_token_factory is old_tok
        finally:
            auth_mod._default_config_factory, auth_mod._default_token_factory = old_cfg, old_tok

    def test_only_token_factory_registered(self):
        sentinel = object()
        old_cfg, old_tok = auth_mod._default_config_factory, auth_mod._default_token_factory
        try:
            auth_mod.set_default_factories(token_factory=lambda: sentinel)
            assert auth_mod._default_token_factory is not None
            assert auth_mod._default_config_factory is old_cfg
        finally:
            auth_mod._default_config_factory, auth_mod._default_token_factory = old_cfg, old_tok

    def test_ellipsis_uses_factories(self):
        cfg, tok = Mock(), Mock()
        old_cfg, old_tok = auth_mod._default_config_factory, auth_mod._default_token_factory
        try:
            auth_mod.set_default_factories(lambda: cfg, lambda: tok)
            svc = AuthService()
            assert svc.config_provider is cfg
            assert svc.token_provider is tok
        finally:
            auth_mod._default_config_factory, auth_mod._default_token_factory = old_cfg, old_tok

    def test_ellipsis_without_factories_raises(self):
        old_cfg, old_tok = auth_mod._default_config_factory, auth_mod._default_token_factory
        try:
            auth_mod._default_config_factory = None
            auth_mod._default_token_factory = None
            with pytest.raises(ValueError, match="No default config factory"):
                AuthService()
            auth_mod._default_config_factory = lambda: Mock()
            with pytest.raises(ValueError, match="No default token factory"):
                AuthService()
        finally:
            auth_mod._default_config_factory, auth_mod._default_token_factory = old_cfg, old_tok


class TestRBACCoverage:
    """RBAC helpers: admin path, grant/revoke, check_permission, roles."""

    def _svc(self):
        return AuthService(Mock(), Mock())

    def test_admin_has_every_permission(self):
        svc = self._svc()
        assert svc.has_permission(User(role=Role.ADMIN), Permission.DELETE_CASES) is True

    def test_check_permission_raises(self):
        svc = self._svc()
        with pytest.raises(PermissionError, match="lacks permission"):
            svc.check_permission(User(role=Role.VIEWER), Permission.DELETE_CASES)

    def test_check_permission_passes_when_granted(self):
        svc = self._svc()
        svc.check_permission(
            User(role=Role.VIEWER, permissions=[Permission.READ_ALERTS]),
            Permission.READ_ALERTS,
        )

    def test_grant_permission_requires_admin(self):
        svc = self._svc()
        target = User(role=Role.ANALYST)
        with pytest.raises(PermissionError, match="Only admins"):
            svc.grant_permission(target, Permission.MANAGE_USERS, admin_user=User(role=Role.VIEWER))

    def test_grant_permission_appends_once(self):
        svc = self._svc()
        admin = User(role=Role.ADMIN)
        target = User(role=Role.ANALYST, permissions=[Permission.READ_ALERTS])
        svc.grant_permission(target, Permission.DELETE_CASES, admin)
        svc.grant_permission(target, Permission.DELETE_CASES, admin)
        assert target.permissions.count(Permission.DELETE_CASES) == 1

    def test_revoke_permission_removes_and_audits(self):
        svc = self._svc()
        target = User(username="u1", permissions=[Permission.READ_ALERTS])
        svc.revoke_permission(target, Permission.READ_ALERTS)
        assert target.permissions == []
        assert svc.audit.events[-1]["action"] == "revoke"

        svc.revoke_permission(target, Permission.READ_ALERTS)  # absent → no audit
        assert len(svc.audit.events) == 1

    @pytest.mark.parametrize(
        "role,expected_subset",
        [
            (Role.ADMIN, list(Permission)),
            (Role.OPERATOR, [Permission.UPDATE_CASES]),
            (Role.ANALYST, [Permission.CREATE_CASES]),
            (Role.VIEWER, [Permission.READ_ALERTS, Permission.READ_CASES]),
            (Role.READONLY, [Permission.READ_ALERTS, Permission.READ_CASES]),
        ],
    )
    def test_get_role_permissions(self, role, expected_subset):
        svc = self._svc()
        perms = svc.get_role_permissions(role)
        for p in expected_subset:
            assert p in perms
        assert svc.get_role_permissions(object()) == []


class TestCanAccessEndpoint:
    """Endpoint RBAC matrix (AUTH-003)."""

    def _svc(self):
        return AuthService(Mock(), Mock())

    def test_admin_accesses_everything(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.ADMIN), "/api/admin/x", "DELETE") is True

    def test_admin_prefix_denied_for_non_admin(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.OPERATOR), "/api/admin/x", "GET") is False
        assert svc.can_access_endpoint(User(role=Role.ANALYST), "/backup", "POST") is False

    def test_auth_paths_open_to_authenticated(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.VIEWER), "/auth/ws-ticket", "POST") is True
        assert svc.can_access_endpoint(User(role=Role.VIEWER), "/api/v1/auth/verify", "GET") is True

    def test_operator_prefix_only_operator(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.OPERATOR), "/api/v1/contain/host", "POST") is True
        assert svc.can_access_endpoint(User(role=Role.ANALYST), "/api/v1/contain/host", "POST") is False

    def test_get_allowed_for_read_roles(self):
        svc = self._svc()
        for role in (Role.VIEWER, Role.READONLY, Role.ANALYST, Role.OPERATOR):
            assert svc.can_access_endpoint(User(role=role), "/api/v1/cases", "GET") is True

    def test_get_falls_back_to_read_permission(self):
        svc = self._svc()
        user = User(role=None, permissions=[Permission.READ_ALERTS])
        user.role = object()  # not a Role member → not in the role tuple
        assert svc.can_access_endpoint(user, "/api/v1/alerts", "GET") is True

    def test_analyst_post_prefixes(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.ANALYST), "/api/v1/alerts", "POST") is True
        assert (
            svc.can_access_endpoint(User(role=Role.OPERATOR), "/api/v1/cache/ioc", "POST") is True
        )
        assert svc.can_access_endpoint(User(role=Role.ANALYST), "/api/v1/other", "POST") is False

    def test_post_allowed_with_create_cases_permission(self):
        svc = self._svc()
        user = User(role=Role.VIEWER, permissions=[Permission.CREATE_CASES])
        assert svc.can_access_endpoint(user, "/api/v1/cases", "POST") is True

    def test_post_denied_without_permission(self):
        svc = self._svc()
        assert svc.can_access_endpoint(User(role=Role.VIEWER), "/api/v1/cases", "POST") is False
