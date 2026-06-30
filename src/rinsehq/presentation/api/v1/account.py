from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from rinsehq.config import get_settings
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.di import (
    CurrentSession,
    get_account_repository,
    get_auth_repository,
    require_permission,
)
from rinsehq.infrastructure.email.smtp_client import NoOpEmailService, SmtpEmailService
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyAccountRepository
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import business_to_response, personal_to_response, sub_admin_to_response

router = APIRouter(prefix="/account", tags=["account"])


class PersonalRequest(BaseModel):
    fullName: str
    phone: str = ""


class BusinessRequest(BaseModel):
    businessName: str = ""
    bio: str = ""
    registrationNo: str = ""
    address: str = ""
    city: str = ""
    postalCode: str = ""
    country: str = "nigeria"
    phone: str = ""
    whatsapp: str = ""


@router.get("/personal")
async def get_personal(
    ctx: CurrentSession,
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    info = await account_repo.get_personal(ctx.user.id)
    return ApiResponse(data=personal_to_response(info))


@router.patch("/personal")
async def update_personal(
    body: PersonalRequest,
    ctx: CurrentSession,
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    await auth_repo.update_personal(ctx.user.id, body.fullName, body.phone)
    info = await account_repo.get_personal(ctx.user.id)
    return ApiResponse(data=personal_to_response(info))


@router.get("/business")
async def get_business(
    ctx: CurrentSession,
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    info = await account_repo.get_business(ctx.user.id)
    return ApiResponse(data=business_to_response(info))


@router.patch("/business")
async def update_business(
    body: BusinessRequest,
    ctx: CurrentSession,
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
) -> ApiResponse[dict]:
    info = await account_repo.update_business(
        ctx.user.id,
        business_name=body.businessName,
        bio=body.bio,
        registration_no=body.registrationNo,
        address=body.address,
        city=body.city,
        postal_code=body.postalCode,
        country=body.country,
        phone=body.phone,
        whatsapp=body.whatsapp,
    )
    return ApiResponse(data=business_to_response(info))
