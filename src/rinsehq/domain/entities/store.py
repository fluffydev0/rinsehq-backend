from __future__ import annotations

from dataclasses import dataclass

from rinsehq.infrastructure.auth.permissions import PermissionLevel, StoreRole


@dataclass(frozen=True)
class Store:
    id: str
    name: str
    address: str
    city: str
    phone: str
    is_main_store: bool
    status: str
    owner_user_id: str


@dataclass(frozen=True)
class StoreAssignment:
    id: str
    store_id: str
    email: str
    name: str
    role: StoreRole
    permission_level: PermissionLevel
    status: str
