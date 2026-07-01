from __future__ import annotations

from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from rinsehq.domain.entities.user import User
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.auth.permissions import has_permission, is_read_only
from rinsehq.infrastructure.db.session import get_db_session
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyBillingRepository,
    SqlAlchemyCatalogRepository,
)
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from rinsehq.infrastructure.repositories.sqlalchemy_store_repository import SqlAlchemyStoreRepository
from rinsehq.infrastructure.security.jwt import decode_access_token
from rinsehq.infrastructure.payments.nomba_client import NombaClient

bearer_scheme = HTTPBearer(auto_error=False)

_nomba_client: NombaClient | None = None


def get_nomba_client() -> NombaClient:
    global _nomba_client
    if _nomba_client is None:
        _nomba_client = NombaClient()
    return _nomba_client


NombaClientDep = Annotated[NombaClient, Depends(get_nomba_client)]

DbSession = Annotated[Session, Depends(get_db_session)]


def get_auth_repository(session: DbSession) -> SqlAlchemyAuthRepository:
    return SqlAlchemyAuthRepository(session)


def get_store_repository(session: DbSession) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_order_repository(session: DbSession) -> SqlAlchemyOrderRepository:
    return SqlAlchemyOrderRepository(session)


def get_catalog_repository(session: DbSession) -> SqlAlchemyCatalogRepository:
    return SqlAlchemyCatalogRepository(session)


def get_billing_repository(session: DbSession) -> SqlAlchemyBillingRepository:
    return SqlAlchemyBillingRepository(session)


def get_account_repository(session: DbSession) -> SqlAlchemyAccountRepository:
    return SqlAlchemyAccountRepository(session)


async def get_current_user(
    session: DbSession,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Not authenticated"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Invalid or expired token"},
        )
    auth_repo = SqlAlchemyAuthRepository(session)
    user = await auth_repo.find_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "User not found"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_session_context(
    session: DbSession,
    user: CurrentUser,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> SessionContext:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Not authenticated"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("store_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Please select a store to continue."},
        )
    store_id = payload["store_id"]
    store_repo = SqlAlchemyStoreRepository(session)
    store = await store_repo.find_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Store not found"},
        )
    assignment = await store_repo.get_assignment(user.id, store_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "You do not have access to this store."},
        )
    role, permission_level, custom = assignment
    return SessionContext(
        user=user,
        store_id=store_id,
        store_name=store.name,
        store_role=role,
        permission_level=permission_level,
        custom_permissions=custom,
    )


CurrentSession = Annotated[SessionContext, Depends(get_session_context)]


def require_permission(capability: str) -> Callable:
    async def _checker(
        request: Request,
        ctx: CurrentSession,
    ) -> SessionContext:
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_read_only(
            ctx.permission_level
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": "Read-only access"},
            )
        if not has_permission(ctx.permission_level, capability, ctx.custom_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": "Insufficient permissions"},
            )
        return ctx

    return _checker


def require_any_permission(*capabilities: str) -> Callable:
    async def _checker(
        request: Request,
        ctx: CurrentSession,
    ) -> SessionContext:
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_read_only(
            ctx.permission_level
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": "Read-only access"},
            )
        if not any(
            has_permission(ctx.permission_level, cap, ctx.custom_permissions)
            for cap in capabilities
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "error": "Insufficient permissions"},
            )
        return ctx

    return _checker
