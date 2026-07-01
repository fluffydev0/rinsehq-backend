from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from rinsehq.config import get_settings
from rinsehq.infrastructure.di import (
    CurrentSession,
    get_billing_repository,
    get_order_repository,
)
from rinsehq.infrastructure.payments.paystack_client import PaystackClient
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import invoice_to_response

router = APIRouter(prefix="/invoices", tags=["invoices"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class PayRequest(BaseModel):
    callbackUrl: str


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    invoice = await billing_repo.find_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Invoice not found"})
    return ApiResponse(data=invoice_to_response(invoice))


@router.post("/{invoice_id}/pay")
async def pay_invoice(
    invoice_id: str,
    body: PayRequest,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    invoice = await billing_repo.find_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Invoice not found"})
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invoice already paid"})
    reference = f"pay_{secrets.token_hex(6)}"
    paystack = PaystackClient()
    result = await paystack.initialize_transaction(
        email=invoice.customer_email or "customer@rinsehq.com",
        amount_kobo=invoice.total,
        reference=reference,
        callback_url=body.callbackUrl,
    )
    return ApiResponse(
        data={"authorizationUrl": result.authorization_url, "reference": result.reference}
    )


@router.get("/{invoice_id}/payment-link")
async def payment_link(
    invoice_id: str,
    ctx: CurrentSession,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    invoice = await billing_repo.find_invoice_for_store(invoice_id, ctx.store_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Invoice not found"})
    settings = get_settings()
    url = f"{settings.app_base_url}/invoice/{invoice_id}"
    return ApiResponse(data={"url": url})


@webhook_router.post("/paystack")
async def paystack_webhook(
    request: Request,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ApiResponse[None]:
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")
    paystack = PaystackClient()
    if paystack.configured and not paystack.verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invalid signature"})

    import json

    event = json.loads(payload)
    event_type = event.get("event")
    data = event.get("data", {})
    reference = data.get("reference", "")

    if event_type == "charge.success":
        from sqlalchemy import select
        from rinsehq.infrastructure.db.models import InvoiceModel, TransactionModel
        from rinsehq.infrastructure.db.session import get_session_factory

        session = get_session_factory()()
        try:
            txn = session.scalar(
                select(TransactionModel).where(TransactionModel.reference == reference)
            )
            if not txn:
                invoice = session.scalar(
                    select(InvoiceModel).where(InvoiceModel.invoice_no.contains(reference[:8]))
                )
                if invoice:
                    await billing_repo.mark_invoice_paid(invoice.id)
                    await billing_repo.update_order_payment(invoice.order_id, "paid", "Paystack")
            else:
                txn.status = "successful"
                session.commit()
        finally:
            session.close()
    elif event_type == "charge.failed":
        pass

    return ApiResponse(data=None)
