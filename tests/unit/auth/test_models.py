"""Unit tests for auth.models User, Permission, Role."""

from __future__ import annotations

from soar_lab.auth.models import Permission, Role, User


class TestPermission:
    """Tests for Permission enum."""

    def test_all_permissions_defined(self):
        assert Permission.ALL.value == "all"
        assert Permission.READ_ALERTS.value == "read_alerts"
        assert Permission.READ_CASES.value == "read_cases"
        assert Permission.CREATE_CASES.value == "create_cases"
        assert Permission.UPDATE_CASES.value == "update_cases"
        assert Permission.DELETE_CASES.value == "delete_cases"
        assert Permission.MANAGE_USERS.value == "manage_users"

    def test_permission_count(self):
        assert len(list(Permission)) == 7


class TestRole:
    """Tests for Role enum."""

    def test_all_roles_defined(self):
        assert Role.ADMIN.value == "admin"
        assert Role.ANALYST.value == "analyst"
        assert Role.READONLY.value == "readonly"

    def test_role_count(self):
        assert len(list(Role)) == 3


class TestUser:
    """Tests for User dataclass."""

    def test_default_values(self):
        u = User()
        assert u.id == ""
        assert u.username == ""
        assert u.role == Role.READONLY
        assert u.permissions == []

    def test_custom_values(self):
        u = User(id="123", username="alice", role=Role.ADMIN, permissions=[Permission.ALL])
        assert u.id == "123"
        assert u.username == "alice"
        assert u.role == Role.ADMIN
        assert u.permissions == [Permission.ALL]

    def test_post_init_none_permissions(self):
        u = User(permissions=None)
        assert u.permissions == []

    def test_post_init_none_role(self):
        u = User(role=None)
        assert u.role == Role.READONLY

    def test_post_init_both_none(self):
        u = User(role=None, permissions=None)
        assert u.role == Role.READONLY
        assert u.permissions == []

    def test_explicit_permissions_preserved(self):
        perms = [Permission.READ_ALERTS, Permission.CREATE_CASES]
        u = User(permissions=perms)
        assert u.permissions == perms
