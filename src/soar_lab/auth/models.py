"""Authentication and authorization data models for the SOAR RBAC system."""

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Permission",
    "Role",
    "User",
]


class Permission(Enum):
    """Permissions used by the SOAR RBAC system."""

    ALL = "all"
    READ_ALERTS = "read_alerts"
    READ_CASES = "read_cases"
    CREATE_CASES = "create_cases"
    UPDATE_CASES = "update_cases"
    DELETE_CASES = "delete_cases"
    MANAGE_USERS = "manage_users"


class Role(Enum):
    """Roles used by the SOAR RBAC system."""

    ADMIN = "admin"
    ANALYST = "analyst"
    READONLY = "readonly"


@dataclass
class User:
    id: str = ""
    username: str = ""
    role: Role = field(default=Role.READONLY)
    permissions: list[Permission] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Apply default values for None permissions and role fields."""
        if self.permissions is None:
            self.permissions = []
        if self.role is None:
            self.role = Role.READONLY
