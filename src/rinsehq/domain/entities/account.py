from __future__ import annotations

from dataclasses import dataclass

from rinsehq.infrastructure.auth.permissions import PermissionLevel


@dataclass(frozen=True)
class PersonalInfo:
    full_name: str
    email: str
    phone: str


@dataclass(frozen=True)
class BusinessInfo:
    business_name: str
    bio: str
    registration_no: str
    address: str
    city: str
    postal_code: str
    country: str
    phone: str
    whatsapp: str


@dataclass(frozen=True)
class AdminPermissions:
    orders: bool
    services: bool
    transactions: bool
    reports: bool
    settings: bool
    admin_management: bool


@dataclass(frozen=True)
class SubAdmin:
    id: str
    name: str
    email: str
    permission_level: PermissionLevel
    permissions: AdminPermissions
    status: str
    store_ids: list[str]
    last_active: str | None = None
