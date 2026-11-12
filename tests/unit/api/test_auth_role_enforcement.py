"""_enforce_role branch coverage: service principals, missing auth_service,
deny path, and OPTIONS preflight in the default-deny middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from soar_lab.auth.models import Role
from soar_lab.interfaces.api.auth import (
    DefaultDenyAuthMiddleware,
    _enforce_role,
)


def _request(path="/api/v1/contain", method="POST", auth_service=None):
    req = MagicMock()
    req.url.path = path
    req.method = method
    req.app.state.auth_service = auth_service
    req.state = MagicMock()
    return req


class TestEnforceRoleEarlyReturns:
    def test_service_principal_skips_role_check(self):
        # should not raise even with a service that would deny everything
        svc = MagicMock()
        svc.can_access_endpoint.return_value = False
        assert _enforce_role(_request(auth_service=svc), {"service": "internal"}) is None
        svc.can_access_endpoint.assert_not_called()

    def test_missing_role_claim_is_readonly_checked(self):
        # AUTH-004: a JWT without a role claim is legacy — resolved to
        # READONLY and the RBAC check now runs (deny-by-default for
        # mutating paths), never silently admin.
        svc = MagicMock()
        svc.can_access_endpoint.return_value = False
        req = _request(auth_service=svc)
        with pytest.raises(HTTPException) as exc:
            _enforce_role(req, {"user": "legacy"})
        assert exc.value.status_code == 403
        called_user = svc.can_access_endpoint.call_args[0][0]
        assert called_user.role == Role.READONLY

    def test_missing_auth_service_skips_check(self):
        assert _enforce_role(_request(auth_service=None), {"user": "u", "role": "viewer"}) is None

    def test_denied_role_raises_403_and_audits(self):
        svc = MagicMock()
        svc.can_access_endpoint.return_value = False
        req = _request(auth_service=svc)
        with pytest.raises(HTTPException) as exc:
            _enforce_role(req, {"user": "viewer-u", "role": "viewer"})
        assert exc.value.status_code == 403


class TestMiddlewarePublic:
    def test_options_preflight_is_public(self):
        mw = DefaultDenyAuthMiddleware(None)
        assert mw._is_public("/api/v1/alerts", "OPTIONS") is True

    def test_root_is_public(self):
        mw = DefaultDenyAuthMiddleware(None)
        assert mw._is_public("/", "GET") is True
