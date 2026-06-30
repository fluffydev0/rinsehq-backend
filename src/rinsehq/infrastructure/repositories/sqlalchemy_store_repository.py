from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from rinsehq.domain.entities.store import Store, StoreAssignment
from rinsehq.domain.entities.user import StoreAccess
from rinsehq.domain.repositories.store_repository import (
    CreateAssignmentInput,
    CreateStoreInput,
    StoreRepository,
)
from rinsehq.infrastructure.auth.permissions import PermissionLevel, StoreRole
from rinsehq.infrastructure.db.id_generator import next_prefixed_id
from rinsehq.infrastructure.db.models import StoreAssignmentModel, StoreModel


class SqlAlchemyStoreRepository(StoreRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def create_store(self, input: CreateStoreInput) -> Store:
        store_id = input.store_id or next_prefixed_id(self._session, "STR-")
        row = StoreModel(
            id=store_id,
            name=input.name,
            address=input.address,
            city=input.city,
            phone=input.phone,
            status=input.status,
            owner_user_id=input.owner_user_id,
            is_main_store=input.is_main_store,
        )
        self._session.add(row)
        self._session.flush()
        return self._store_entity(row)

    async def find_by_id(self, store_id: str) -> Optional[Store]:
        row = self._session.get(StoreModel, store_id)
        return self._store_entity(row) if row else None

    async def list_owned_stores(self, owner_user_id: str) -> list[Store]:
        rows = self._session.scalars(
            select(StoreModel).where(StoreModel.owner_user_id == owner_user_id)
        ).all()
        return [self._store_entity(r) for r in rows]

    async def list_accessible_stores(self, user_id: str) -> list[StoreAccess]:
        owned = self._session.scalars(
            select(StoreModel).where(StoreModel.owner_user_id == user_id)
        ).all()
        assignments = self._session.scalars(
            select(StoreAssignmentModel).where(
                StoreAssignmentModel.user_id == user_id,
                StoreAssignmentModel.status == "active",
            )
        ).all()

        result: list[StoreAccess] = []
        seen: set[str] = set()
        for store in owned:
            seen.add(store.id)
            result.append(
                StoreAccess(
                    store_id=store.id,
                    store_name=store.name,
                    address=store.address,
                    city=store.city,
                    is_main_store=store.is_main_store,
                    role="owner",
                    permission_level="full_admin",
                )
            )
        for asn in assignments:
            if asn.store_id in seen:
                continue
            store = self._session.get(StoreModel, asn.store_id)
            if not store:
                continue
            result.append(
                StoreAccess(
                    store_id=store.id,
                    store_name=store.name,
                    address=store.address,
                    city=store.city,
                    is_main_store=store.is_main_store,
                    role=asn.role,  # type: ignore[arg-type]
                    permission_level=asn.permission_level,  # type: ignore[arg-type]
                )
            )
        return result

    async def update_store(self, store_id: str, **fields: object) -> Optional[Store]:
        row = self._session.get(StoreModel, store_id)
        if not row:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        self._session.flush()
        return self._store_entity(row)

    async def get_assignment(
        self, user_id: str, store_id: str
    ) -> Optional[tuple[StoreRole, PermissionLevel, dict | None]]:
        store = self._session.get(StoreModel, store_id)
        if not store:
            return None
        if store.owner_user_id == user_id:
            return "owner", "full_admin", None
        asn = self._session.scalar(
            select(StoreAssignmentModel).where(
                StoreAssignmentModel.user_id == user_id,
                StoreAssignmentModel.store_id == store_id,
                StoreAssignmentModel.status == "active",
            )
        )
        if not asn:
            return None
        return (
            asn.role,  # type: ignore[return-value]
            asn.permission_level,  # type: ignore[return-value]
            asn.custom_permissions,
        )

    async def list_assignments(self, store_id: str) -> list[StoreAssignment]:
        rows = self._session.scalars(
            select(StoreAssignmentModel).where(StoreAssignmentModel.store_id == store_id)
        ).all()
        return [self._assignment_entity(r) for r in rows]

    async def create_assignment(self, input: CreateAssignmentInput) -> StoreAssignment:
        asn_id = next_prefixed_id(self._session, "ASG-")
        row = StoreAssignmentModel(
            id=asn_id,
            store_id=input.store_id,
            user_id=input.user_id,
            email=input.email,
            name=input.name,
            role=input.role,
            permission_level=input.permission_level,
            custom_permissions=input.custom_permissions,
        )
        self._session.add(row)
        self._session.flush()
        return self._assignment_entity(row)

    async def list_all_assignments_for_owner(self, owner_user_id: str) -> list[StoreAssignment]:
        store_ids = [
            s.id
            for s in self._session.scalars(
                select(StoreModel).where(StoreModel.owner_user_id == owner_user_id)
            ).all()
        ]
        if not store_ids:
            return []
        rows = self._session.scalars(
            select(StoreAssignmentModel).where(StoreAssignmentModel.store_id.in_(store_ids))
        ).all()
        return [self._assignment_entity(r) for r in rows]

    async def deactivate_assignment(self, assignment_id: str) -> None:
        row = self._session.get(StoreAssignmentModel, assignment_id)
        if row:
            row.status = "inactive"
            self._session.flush()

    @staticmethod
    def _store_entity(row: StoreModel) -> Store:
        return Store(
            id=row.id,
            name=row.name,
            address=row.address,
            city=row.city,
            phone=row.phone,
            is_main_store=row.is_main_store,
            status=row.status,
            owner_user_id=row.owner_user_id,
        )

    @staticmethod
    def _assignment_entity(row: StoreAssignmentModel) -> StoreAssignment:
        return StoreAssignment(
            id=row.id,
            store_id=row.store_id,
            email=row.email,
            name=row.name,
            role=row.role,  # type: ignore[arg-type]
            permission_level=row.permission_level,  # type: ignore[arg-type]
            status=row.status,
        )
