from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from rinsehq.domain.entities.store import Store, StoreAssignment
from rinsehq.domain.entities.user import StoreAccess
from rinsehq.infrastructure.auth.permissions import PermissionLevel, StoreRole


@dataclass(frozen=True)
class CreateStoreInput:
    name: str
    address: str
    city: str
    phone: str
    status: str
    owner_user_id: str
    is_main_store: bool = False
    store_id: str | None = None


@dataclass(frozen=True)
class CreateAssignmentInput:
    store_id: str
    user_id: str
    email: str
    name: str
    role: StoreRole
    permission_level: PermissionLevel
    custom_permissions: dict[str, bool] | None = None


class StoreRepository(Protocol):
    async def create_store(self, input: CreateStoreInput) -> Store: ...

    async def find_by_id(self, store_id: str) -> Optional[Store]: ...

    async def list_owned_stores(self, owner_user_id: str) -> list[Store]: ...

    async def list_accessible_stores(self, user_id: str) -> list[StoreAccess]: ...

    async def update_store(self, store_id: str, **fields: object) -> Optional[Store]: ...

    async def get_assignment(
        self, user_id: str, store_id: str
    ) -> Optional[tuple[StoreRole, PermissionLevel, dict | None]]: ...

    async def list_assignments(self, store_id: str) -> list[StoreAssignment]: ...

    async def create_assignment(self, input: CreateAssignmentInput) -> StoreAssignment: ...

    async def list_all_assignments_for_owner(self, owner_user_id: str) -> list[StoreAssignment]: ...

    async def deactivate_assignment(self, assignment_id: str) -> None: ...
