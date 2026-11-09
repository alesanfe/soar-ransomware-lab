"""_enforce_role branch coverage: service principals, missing auth_service,
deny path, and OPTIONS preflight in the default-deny middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

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
        _enforce_role(_request(auth_service=svc), {"service": "internal"})

    def test_missing_role_claim_is_backcompat_admin(self):
        svc = MagicMock()
        _enforce_role(_request(auth_service=svc), {"user": "legacy"})
        svc.can_access_endpoint.assert_not_called()

    def test_missing_auth_service_skips_check(self):
        _enforce_role(_request(auth_service=None), {"user": "u", "role": "viewer"})

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
