#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Authorization Tests
Tests for RBAC (Role-Based Access Control) authorization
"""

import pytest
from soar_lab.auth.models import User, Role, Permission
from soar_lab.auth.service import AuthService
from unittest.mock import Mock, patch


class TestAuthorizationRBAC:
    """Test RBAC authorization system"""

    @pytest.fixture
    def auth_service(self):
        """Create auth service for testing"""
        return AuthService()

    @pytest.fixture
    def admin_user(self):
        """Create admin user with all permissions"""
        return User(
            id="admin-001",
            username="admin",
            role=Role.ADMIN,
            permissions=[Permission.ALL]
        )

    @pytest.fixture
    def analyst_user(self):
        """Create analyst user with limited permissions"""
        return User(
            id="analyst-001",
            username="analyst",
            role=Role.ANALYST,
            permissions=[
                Permission.READ_ALERTS,
                Permission.READ_CASES,
                Permission.CREATE_CASES
            ]
        )

    @pytest.fixture
    def readonly_user(self):
        """Create readonly user with minimal permissions"""
        return User(
            id="readonly-001",
            username="readonly",
            role=Role.READONLY,
            permissions=[Permission.READ_ALERTS, Permission.READ_CASES]
        )

    def test_admin_has_all_permissions(self, auth_service, admin_user):
        """Test that admin user has all permissions"""
        for permission in Permission:
            assert auth_service.has_permission(admin_user, permission), \
                f"Admin should have {permission} permission"

    def test_analyst_has_limited_permissions(self, auth_service, analyst_user):
        """Test that analyst user has only assigned permissions"""
        assert auth_service.has_permission(analyst_user, Permission.READ_ALERTS)
        assert auth_service.has_permission(analyst_user, Permission.READ_CASES)
        assert auth_service.has_permission(analyst_user, Permission.CREATE_CASES)

        # Should not have admin permissions
        assert not auth_service.has_permission(analyst_user, Permission.DELETE_CASES)
        assert not auth_service.has_permission(analyst_user, Permission.MANAGE_USERS)

    def test_readonly_user_cannot_modify(self, auth_service, readonly_user):
        """Test that readonly user cannot modify data"""
        assert auth_service.has_permission(readonly_user, Permission.READ_ALERTS)
        assert auth_service.has_permission(readonly_user, Permission.READ_CASES)

        # Should not have write permissions
        assert not auth_service.has_permission(readonly_user, Permission.CREATE_CASES)
        assert not auth_service.has_permission(readonly_user, Permission.UPDATE_CASES)
        assert not auth_service.has_permission(readonly_user, Permission.DELETE_CASES)

    def test_user_without_permission_denied(self, auth_service, readonly_user):
        """Test that users without permissions are denied access"""
        with pytest.raises(PermissionError):
            auth_service.check_permission(readonly_user, Permission.DELETE_CASES)

    def test_privilege_escalation_prevented(self, auth_service, analyst_user):
        """Test that privilege escalation is prevented"""
        # Try to grant admin permissions to analyst
        with pytest.raises(PermissionError):
            auth_service.grant_permission(analyst_user, Permission.MANAGE_USERS, admin_user=analyst_user)

    def test_protected_endpoint_access(self, auth_service, analyst_user):
        """Test access to protected endpoints"""
        # Analyst can access read endpoints
        assert auth_service.can_access_endpoint(analyst_user, "/api/alerts", "GET")
        assert auth_service.can_access_endpoint(analyst_user, "/api/cases", "GET")

        # Analyst cannot access admin endpoints
        assert not auth_service.can_access_endpoint(analyst_user, "/api/admin/users", "GET")
        assert not auth_service.can_access_endpoint(analyst_user, "/api/admin/config", "POST")

    def test_role_based_access_control(self, auth_service):
        """Test role-based access control"""
        admin = User(id="admin", username="admin", role=Role.ADMIN)
        analyst = User(id="analyst", username="analyst", role=Role.ANALYST)
        readonly = User(id="readonly", username="readonly", role=Role.READONLY)

        # Admin can access everything
        assert auth_service.can_access_endpoint(admin, "/api/admin/*", "*")

        # Analyst can access analysis endpoints
        assert auth_service.can_access_endpoint(analyst, "/api/cases", "GET")
        assert auth_service.can_access_endpoint(analyst, "/api/cases", "POST")
        assert not auth_service.can_access_endpoint(analyst, "/api/admin/*", "*")

        # Readonly can only read
        assert auth_service.can_access_endpoint(readonly, "/api/cases", "GET")
        assert not auth_service.can_access_endpoint(readonly, "/api/cases", "POST")

    def test_permission_inheritance(self, auth_service):
        """Test that roles inherit permissions correctly"""
        admin = User(id="admin", username="admin", role=Role.ADMIN)

        # Admin role should inherit all permissions
        assert len(auth_service.get_role_permissions(Role.ADMIN)) == len(Permission)

    def test_permission_revocation(self, auth_service, analyst_user):
        """Test that permissions can be revoked"""
        auth_service.revoke_permission(analyst_user, Permission.CREATE_CASES)

        assert not auth_service.has_permission(analyst_user, Permission.CREATE_CASES)
        assert auth_service.has_permission(analyst_user, Permission.READ_ALERTS)

    def test_temporary_permission_grant(self, auth_service, readonly_user):
        """Test temporary permission grants"""
        # Grant temporary permission
        auth_service.grant_temporary_permission(
            readonly_user,
            Permission.CREATE_CASES,
            duration_seconds=60
        )

        assert auth_service.has_permission(readonly_user, Permission.CREATE_CASES)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
