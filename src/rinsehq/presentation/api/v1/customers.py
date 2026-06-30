from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from rinsehq.infrastructure.di import CurrentSession, get_catalog_repository, require_permission
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyCatalogRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import customer_to_response

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
async def search_customers(
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
    search: str = Query("", min_length=0),
) -> ApiResponse[list]:
    if not search:
        return ApiResponse(data=[])
    customers = await catalog_repo.search_customers(ctx.store_id, search)
    return ApiResponse(data=[customer_to_response(c) for c in customers])
