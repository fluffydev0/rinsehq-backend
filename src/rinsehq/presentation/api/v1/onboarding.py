from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from rinsehq.config import get_settings
from rinsehq.infrastructure.di import (
    CurrentSession,
    CurrentUser,
    get_account_repository,
    get_auth_repository,
    get_catalog_repository,
    get_store_repository,
    require_permission,
)
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyAccountRepository
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyCatalogRepository
from rinsehq.infrastructure.repositories.sqlalchemy_store_repository import SqlAlchemyStoreRepository
from rinsehq.infrastructure.storage.cloudinary_client import CloudinaryStorageService, LocalStorageService
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import business_to_response, config_to_response

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_DOC = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp"}


class BusinessAddressRequest(BaseModel):
    address: str
    city: str
    postalCode: str = ""
    country: str = "nigeria"
    phone: str
    whatsapp: str = ""


class BusinessServicesRequest(BaseModel):
    laundryModes: list[str]
    serviceTypes: list[str]
    orderTypes: list[str]


def _storage():
    return CloudinaryStorageService() if get_settings().cloudinary_configured else LocalStorageService()


@router.post("/business-info")
async def business_info(
    user: CurrentUser,
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
    businessName: str = Form(...),
    businessBio: str = Form(""),
    registrationNo: str = Form(""),
    businessDocument: Optional[UploadFile] = File(None),
    businessLogo: Optional[UploadFile] = File(None),
    businessBanner: Optional[UploadFile] = File(None),
) -> ApiResponse[dict]:
    storage = _storage()
    logo_url = banner_url = document_url = None
    if businessLogo:
        content = await businessLogo.read()
        if len(content) <= MAX_FILE_SIZE:
            logo_url = (await storage.upload_file(content, businessLogo.filename or "logo.png")).secure_url
    if businessBanner:
        content = await businessBanner.read()
        if len(content) <= MAX_FILE_SIZE:
            banner_url = (await storage.upload_file(content, businessBanner.filename or "banner.png")).secure_url
    if businessDocument:
        content = await businessDocument.read()
        if len(content) <= MAX_FILE_SIZE:
            rt = "raw" if businessDocument.content_type == "application/pdf" else "image"
            document_url = (
                await storage.upload_file(content, businessDocument.filename or "doc.pdf", rt)
            ).secure_url
    info = await account_repo.update_business(
        user.id,
        business_name=businessName,
        bio=businessBio,
        registration_no=registrationNo,
    )
    if any([logo_url, banner_url, document_url]):
        info = await account_repo.update_business_profile_files(
            user.id, logo_url, banner_url, document_url
        )
    return ApiResponse(data=business_to_response(info))


@router.post("/business-address")
async def business_address(
    body: BusinessAddressRequest,
    user: CurrentUser,
    account_repo: Annotated[SqlAlchemyAccountRepository, Depends(get_account_repository)],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[dict]:
    info = await account_repo.update_business(
        user.id,
        address=body.address,
        city=body.city,
        postal_code=body.postalCode,
        country=body.country,
        phone=body.phone,
        whatsapp=body.whatsapp or body.phone,
    )
    stores = await store_repo.list_owned_stores(user.id)
    main = next((s for s in stores if s.is_main_store), stores[0] if stores else None)
    if main:
        await store_repo.update_store(
            main.id,
            address=body.address,
            city=body.city,
            phone=body.phone,
        )
    return ApiResponse(data=business_to_response(info))


@router.post("/business-services")
async def business_services(
    body: BusinessServicesRequest,
    ctx: Annotated[object, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    from rinsehq.domain.entities.service import ConfigItem, ServicesConfiguration
    from rinsehq.infrastructure.auth.context import SessionContext

    session: SessionContext = ctx  # type: ignore[assignment]
    config = ServicesConfiguration(
        laundry_modes=[ConfigItem(id=f"m{i}", label=l, enabled=True) for i, l in enumerate(body.laundryModes)],
        service_types=[ConfigItem(id=f"s{i}", label=l, enabled=True) for i, l in enumerate(body.serviceTypes)],
        order_types=[ConfigItem(id=f"o{i}", label=l, enabled=True) for i, l in enumerate(body.orderTypes)],
    )
    saved = await catalog_repo.set_config(session.store_id, config)
    await catalog_repo.seed_default_services(session.store_id, body.laundryModes)
    return ApiResponse(data=config_to_response(saved))


@router.post("/complete")
async def complete_onboarding(
    user: CurrentUser,
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> ApiResponse[None]:
    await auth_repo.set_onboarding_completed(user.id)
    return ApiResponse(data=None)
