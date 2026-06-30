from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from rinsehq.config import get_settings
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.di import get_account_repository, require_permission
from rinsehq.infrastructure.email.smtp_client import NoOpEmailService, SmtpEmailService
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyAccountRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import sub_admin_to_response

router = APIRouter(prefix="/admins", tags=["admins"])


class PermissionsRequest(BaseModel):
    orders: bool = True
    services: bool = True
    transactions: bool = True
    reports: bool = True
    settings: bool = False
    adminManagement: bool = False


class SubAdminRequest(BaseModel):
    name: str
    email: EmailStr
    permissionLevel: str = "manager"
    permissions: PermissionsRequest
    status: str = "active"
    storeIds: list[str]


def _email_service():
    settings = get_settings()
    if settings.smtp_user and settings.smtp_password_clean:
        return SmtpEmailService()
    return NoOpEmailService()


@router.get("")
async def list_admins(
    ctx: Annotated[SessionContext, Depends(require_permission("adminManagement"))],
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[list]:
    admins = await account_repo.list_sub_admins(ctx.user.id)
    return ApiResponse(data=[sub_admin_to_response(a) for a in admins])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: SubAdminRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("adminManagement"))],
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    temp_password = secrets.token_urlsafe(10)
    admin = await account_repo.create_sub_admin(
        ctx.user.id,
        body.name,
        body.email,
        body.permissionLevel,  # type: ignore[arg-type]
        body.permissions.model_dump(),
        body.status,
        body.storeIds,
        temp_password,
    )
    settings = get_settings()
    await _email_service().send_admin_invitation(
        body.email, body.name, f"{settings.app_base_url}/login"
    )
    return ApiResponse(data=sub_admin_to_response(admin))


@router.patch("/{admin_id}")
async def update_admin(
    admin_id: str,
    body: SubAdminRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("adminManagement"))],
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    admin = await account_repo.update_sub_admin(
        admin_id,
        ctx.user.id,
        name=body.name,
        permission_level=body.permissionLevel,
        permissions=body.permissions.model_dump(),
        status=body.status,
    )
    if not admin:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Admin not found"})
    return ApiResponse(data=sub_admin_to_response(admin))


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("adminManagement"))],
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> None:
    deleted = await account_repo.delete_sub_admin(admin_id, ctx.user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Admin not found"})
