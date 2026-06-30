from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from rinsehq.domain.repositories.store_repository import CreateAssignmentInput, CreateStoreInput
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.di import (
    CurrentSession,
    CurrentUser,
    get_auth_repository,
    get_store_repository,
    require_permission,
)
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_store_repository import SqlAlchemyStoreRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import assignment_to_response, store_access_to_response, store_to_response

router = APIRouter(prefix="/stores", tags=["stores"])


class StoreFormRequest(BaseModel):
    name: str
    address: str
    city: str
    phone: str
    status: str = "active"


class AssignmentRequest(BaseModel):
    email: str
    name: str
    role: str = "manager"
    permissionLevel: str = "manager"


@router.get("/accessible")
async def accessible_stores(
    user: CurrentUser,
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[list]:
    stores = await store_repo.list_accessible_stores(user.id)
    return ApiResponse(data=[store_access_to_response(s) for s in stores])


@router.get("")
async def list_stores(
    ctx: CurrentSession,
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[list]:
    stores = await store_repo.list_owned_stores(ctx.user.id)
    return ApiResponse(data=[store_to_response(s) for s in stores])


@router.get("/{store_id}")
async def get_store(
    store_id: str,
    ctx: CurrentSession,
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[dict]:
    store = await store_repo.find_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Store not found"})
    assignment = await store_repo.get_assignment(ctx.user.id, store_id)
    if not assignment and store.owner_user_id != ctx.user.id:
        raise HTTPException(status_code=403, detail={"success": False, "error": "Access denied"})
    return ApiResponse(data=store_to_response(store))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_store(
    body: StoreFormRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("settings"))],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[dict]:
    store = await store_repo.create_store(
        CreateStoreInput(
            name=body.name,
            address=body.address,
            city=body.city,
            phone=body.phone,
            status=body.status,
            owner_user_id=ctx.user.id,
        )
    )
    return ApiResponse(data=store_to_response(store))


@router.patch("/{store_id}")
async def update_store(
    store_id: str,
    body: StoreFormRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("settings"))],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[dict]:
    store = await store_repo.update_store(
        store_id,
        name=body.name,
        address=body.address,
        city=body.city,
        phone=body.phone,
        status=body.status,
    )
    if not store:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Store not found"})
    return ApiResponse(data=store_to_response(store))


@router.get("/{store_id}/assignments")
async def list_assignments(
    store_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("settings"))],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[list]:
    items = await store_repo.list_assignments(store_id)
    return ApiResponse(data=[assignment_to_response(a) for a in items])


@router.post("/{store_id}/assignments", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    store_id: str,
    body: AssignmentRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("settings"))],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> ApiResponse[dict]:
    from rinsehq.domain.repositories.auth_repository import CreateUserInput
    import secrets

    user = await auth_repo.find_by_email(body.email)
    if not user:
        user = await auth_repo.create(
            CreateUserInput(
                email=body.email,
                password=secrets.token_urlsafe(12),
                name=body.name,
            )
        )
    assignment = await store_repo.create_assignment(
        CreateAssignmentInput(
            store_id=store_id,
            user_id=user.id,
            email=body.email,
            name=body.name,
            role=body.role,  # type: ignore[arg-type]
            permission_level=body.permissionLevel,  # type: ignore[arg-type]
        )
    )
    return ApiResponse(data=assignment_to_response(assignment))
