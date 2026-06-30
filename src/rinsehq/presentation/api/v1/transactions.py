from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.di import (
    CurrentSession,
    get_billing_repository,
    require_permission,
)
from rinsehq.infrastructure.payments.paystack_client import PaystackClient
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository
from rinsehq.presentation.helpers import unwrap_result
from rinsehq.presentation.schemas.envelope import ApiResponse, PaginationMeta
from rinsehq.presentation.schemas.mappers import transaction_detail_to_response, transaction_row_to_response

router = APIRouter(prefix="/transactions", tags=["transactions"])


class RefundRequest(BaseModel):
    reason: str = ""


@router.get("")
async def list_transactions(
    ctx: Annotated[SessionContext, Depends(require_permission("transactions"))],
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
    status: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse[list]:
    items, total = await billing_repo.list_transactions(
        ctx.store_id, status, type, page, limit
    )
    return ApiResponse(
        data=[transaction_row_to_response(t) for t in items],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get("/{txn_id}")
async def get_transaction(
    txn_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("transactions"))],
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    txn = await billing_repo.find_transaction(txn_id, ctx.store_id)
    if not txn:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Transaction not found"})
    return ApiResponse(data=transaction_detail_to_response(txn))


@router.post("/{txn_id}/refund")
async def refund_transaction(
    txn_id: str,
    body: RefundRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("transactions"))],
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    txn = await billing_repo.find_transaction(txn_id, ctx.store_id)
    if not txn:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Transaction not found"})
    paystack = PaystackClient()
    await paystack.refund_transaction(txn.reference, body.reason)
    refund = await billing_repo.create_refund_transaction(txn_id, body.reason, ctx.store_id)
    return ApiResponse(data=transaction_detail_to_response(refund))
