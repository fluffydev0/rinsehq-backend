from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from rinsehq.domain.entities.service import ConfigItem, ServicesConfiguration
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.di import CurrentSession, get_catalog_repository, require_permission
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyCatalogRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import config_to_response, service_to_response

router = APIRouter(prefix="/services", tags=["services"])


class ServiceFormRequest(BaseModel):
    name: str
    category: str
    laundryMode: str
    unitPrice: int
    pricingUnit: str
    turnaroundHours: int = 24
    status: str = "active"
    description: str = ""


class StatusRequest(BaseModel):
    status: str


class ConfigItemRequest(BaseModel):
    id: str
    label: str
    enabled: bool = True


class ConfigRequest(BaseModel):
    laundryModes: list[ConfigItemRequest]
    serviceTypes: list[ConfigItemRequest]
    orderTypes: list[ConfigItemRequest]


class AddConfigItemRequest(BaseModel):
    section: str
    label: str


@router.get("")
async def list_services(
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> ApiResponse[list]:
    services = await catalog_repo.list_services(ctx.store_id, status, category)
    return ApiResponse(data=[service_to_response(s) for s in services])


@router.get("/summary")
async def services_summary(
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    return ApiResponse(data=await catalog_repo.service_summary(ctx.store_id))


@router.get("/config")
async def get_config(
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    config = await catalog_repo.get_config(ctx.store_id)
    return ApiResponse(data=config_to_response(config))


@router.put("/config")
async def put_config(
    body: ConfigRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    config = ServicesConfiguration(
        laundry_modes=[ConfigItem(id=i.id, label=i.label, enabled=i.enabled) for i in body.laundryModes],
        service_types=[ConfigItem(id=i.id, label=i.label, enabled=i.enabled) for i in body.serviceTypes],
        order_types=[ConfigItem(id=i.id, label=i.label, enabled=i.enabled) for i in body.orderTypes],
    )
    saved = await catalog_repo.set_config(ctx.store_id, config)
    return ApiResponse(data=config_to_response(saved))


@router.post("/config/items")
async def add_config_item(
    body: AddConfigItemRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    config = await catalog_repo.add_config_item(ctx.store_id, body.section, body.label)
    return ApiResponse(data=config_to_response(config))


@router.get("/{service_id}")
async def get_service(
    service_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    service = await catalog_repo.find_service(service_id, ctx.store_id)
    if not service:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Service not found"})
    return ApiResponse(data=service_to_response(service))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_service(
    body: ServiceFormRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    service = await catalog_repo.create_service(
        ctx.store_id,
        name=body.name,
        category=body.category,
        laundry_mode=body.laundryMode,
        unit_price=body.unitPrice,
        pricing_unit=body.pricingUnit,
        turnaround_hours=body.turnaroundHours,
        status=body.status,
        description=body.description,
    )
    return ApiResponse(data=service_to_response(service))


@router.patch("/{service_id}")
async def update_service(
    service_id: str,
    body: ServiceFormRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    service = await catalog_repo.update_service(
        service_id,
        ctx.store_id,
        name=body.name,
        category=body.category,
        laundry_mode=body.laundryMode,
        unit_price=body.unitPrice,
        pricing_unit=body.pricingUnit,
        turnaround_hours=body.turnaroundHours,
        status=body.status,
        description=body.description,
    )
    if not service:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Service not found"})
    return ApiResponse(data=service_to_response(service))


@router.patch("/{service_id}/status")
async def update_service_status(
    service_id: str,
    body: StatusRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("services"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> ApiResponse[dict]:
    service = await catalog_repo.update_service(service_id, ctx.store_id, status=body.status)
    if not service:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Service not found"})
    return ApiResponse(data=service_to_response(service))
