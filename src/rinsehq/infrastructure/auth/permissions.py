from __future__ import annotations

from typing import Literal

PermissionLevel = Literal["full_admin", "manager", "staff", "viewer"]
StoreRole = Literal["owner", "manager", "sub_admin"]

DEFAULT_PERMISSIONS: dict[PermissionLevel, dict[str, bool]] = {
    "full_admin": {
        "orders": True,
        "services": True,
        "transactions": True,
        "reports": True,
        "settings": True,
        "adminManagement": True,
    },
    "manager": {
        "orders": True,
        "services": True,
        "transactions": True,
        "reports": True,
        "settings": False,
        "adminManagement": False,
    },
    "staff": {
        "orders": True,
        "services": False,
        "transactions": False,
        "reports": False,
        "settings": False,
        "adminManagement": False,
    },
    "viewer": {
        "orders": True,
        "services": True,
        "transactions": True,
        "reports": True,
        "settings": False,
        "adminManagement": False,
    },
}


def resolve_permissions(
    permission_level: PermissionLevel, custom: dict[str, bool] | None = None
) -> dict[str, bool]:
    base = dict(DEFAULT_PERMISSIONS[permission_level])
    if custom:
        base.update(custom)
    return base


def has_permission(
    permission_level: PermissionLevel,
    capability: str,
    custom: dict[str, bool] | None = None,
) -> bool:
    perms = resolve_permissions(permission_level, custom)
    return perms.get(capability, False)


def is_read_only(permission_level: PermissionLevel) -> bool:
    return permission_level == "viewer"
