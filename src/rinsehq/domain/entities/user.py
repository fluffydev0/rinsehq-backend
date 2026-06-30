from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rinsehq.infrastructure.auth.permissions import PermissionLevel, StoreRole


@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str
    created_at: datetime
    email_verified: bool = False
    phone: str = ""
    onboarding_completed: bool = False


@dataclass(frozen=True)
class UserCredentials:
    email: str
    password: str


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    name: str | None
    store_id: str
    store_name: str
    store_role: StoreRole
    permission_level: PermissionLevel


@dataclass(frozen=True)
class StoreAccess:
    store_id: str
    store_name: str
    address: str
    city: str
    is_main_store: bool
    role: StoreRole
    permission_level: PermissionLevel
