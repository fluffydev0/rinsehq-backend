from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from rinsehq.config import Settings, get_settings
from rinsehq.infrastructure.di import (
    CurrentSession,
    NombaClientDep,
    get_billing_repository,
)
from rinsehq.infrastructure.payments.nomba_client import NombaCheckoutError, NombaClient, NombaVirtualAccountError
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import invoice_to_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class PayRequest(BaseModel):
    callbackUrl: str


def _invoice_payment_reference(invoice_no: str) -> str:
    return f"rinse_inv_{invoice_no.replace('-', '_').lower()}"


def _virtual_account_ref(invoice_no: str) -> str:
    return f"rinse_{invoice_no.replace('-', '_').lower()}"


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
    nomba: NombaClientDep,
) -> ApiResponse[dict]:
    invoice = await billing_repo.find_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Invoice not found"})
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invoice already paid"})

    order_reference = _invoice_payment_reference(invoice.invoice_no)
    existing = await billing_repo.find_transaction_by_reference(order_reference)
    if existing and existing.status == "successful":
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invoice already paid"})

    try:
        result = await nomba.create_checkout(
            amount_kobo=invoice.total,
            customer_email=invoice.customer_email or "customer@rinsehq.app",
            callback_url=body.callbackUrl,
            order_reference=order_reference,
        )
    except NombaCheckoutError as exc:
        logger.error("Nomba checkout failed for invoice %s: %s", invoice_id, exc)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Payment provider unavailable. Please try again."},
        ) from exc

    if not existing:
        await billing_repo.create_payment_transaction(
            store_id=invoice.store_id,
            order_id=invoice.order_id,
            reference=order_reference,
            customer=invoice.customer_name,
            amount_cents=invoice.total,
            type="payment",
            payment_method="Nomba",
            status="pending",
            customer_email=invoice.customer_email or "",
            customer_phone=invoice.customer_phone or "",
        )

    return ApiResponse(
        data={
            "authorizationUrl": result.checkout_url,
            "reference": result.order_reference,
        }
    )


@router.post("/{invoice_id}/virtual-account")
async def get_invoice_virtual_account(
    invoice_id: str,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
    nomba: NombaClientDep,
) -> ApiResponse[dict]:
    invoice = await billing_repo.find_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail={"success": False, "error": "Invoice not found"})
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail={"success": False, "error": "Invoice already paid"})

    account_ref = _virtual_account_ref(invoice.invoice_no)
    account_name = f"RinseHQ — {invoice.invoice_no}"

    try:
        va = await nomba.create_virtual_account(
            account_ref=account_ref,
            account_name=account_name,
            expected_amount_kobo=invoice.total,
        )
    except NombaVirtualAccountError as exc:
        logger.error("Virtual account creation failed for invoice %s: %s", invoice_id, exc)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Could not generate account number. Please try again."},
        ) from exc

    va_reference = f"va_{account_ref}"
    existing = await billing_repo.find_transaction_by_reference(va_reference)
    if not existing:
        await billing_repo.create_payment_transaction(
            store_id=invoice.store_id,
            order_id=invoice.order_id,
            reference=va_reference,
            customer=invoice.customer_name,
            amount_cents=invoice.total,
            type="payment",
            payment_method="Nomba",
            status="pending",
            channel="bank_transfer",
            customer_email=invoice.customer_email or "",
            customer_phone=invoice.customer_phone or "",
        )

    return ApiResponse(
        data={
            "accountNumber": va.account_number,
            "bankName": va.bank_name,
            "accountName": va.account_name,
            "reference": account_ref,
            "amountDue": invoice.total,
        }
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


@webhook_router.post("/nomba", include_in_schema=False)
async def nomba_webhook(
    request: Request,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("nomba-signature", "")

    if not settings.nomba_webhook_secret:
        logger.warning("NOMBA_WEBHOOK_SECRET not set — skipping signature verification (dev mode)")
    elif not NombaClient.verify_webhook(raw_body, signature, settings.nomba_webhook_secret):
        logger.warning("Nomba webhook signature mismatch — rejecting")
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "Invalid webhook signature"},
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Invalid JSON payload"},
        ) from exc

    event_type: str = payload.get("event_type", payload.get("event", ""))
    data: dict = payload.get("data", {})
    logger.info("Nomba webhook received: event=%s", event_type)

    if event_type == "payment_success":
        txn_data = data.get("transaction", data)
        reference = txn_data.get("merchantTxRef") or txn_data.get("orderReference", "")

        if not reference:
            logger.error("Nomba payment_success missing reference: %s", payload)
            return Response(status_code=200)

        txn = await billing_repo.find_transaction_by_reference(reference)
        if txn and txn.status == "successful":
            logger.info("Duplicate payment_success for reference=%s — ignoring", reference)
            return Response(status_code=200)

        amount_raw = txn_data.get("transactionAmount", txn_data.get("amount", 0))
        fee_raw = txn_data.get("fee", 0)
        channel = txn_data.get("type", txn_data.get("channel", "card"))
        # Nomba webhook amounts may be in Naira — convert to kobo if value looks like Naira
        amount_kobo = int(amount_raw * 100) if amount_raw and amount_raw < 1_000_000 else int(amount_raw)
        fee_kobo = int(fee_raw * 100) if fee_raw and fee_raw < 1_000_000 else int(fee_raw)
        net_kobo = amount_kobo - fee_kobo

        if txn:
            await billing_repo.mark_transaction_successful(
                txn.id,
                channel=channel,
                fee_kobo=fee_kobo,
                net_kobo=net_kobo,
            )
            order_id = txn.order_id
        else:
            logger.warning(
                "payment_success received but no pending transaction for ref=%s",
                reference,
            )
            return Response(status_code=200)

        invoice = await billing_repo.find_invoice_by_order_id(order_id)
        if invoice and invoice.status != "paid":
            await billing_repo.mark_invoice_paid(invoice.id)
            logger.info("Invoice %s marked paid", invoice.id)

        await billing_repo.update_order_payment(order_id, "paid", "Nomba")
        logger.info("Order %s payment_status=paid via Nomba", order_id)

    elif event_type == "payment_failed":
        txn_data = data.get("transaction", data)
        reference = txn_data.get("merchantTxRef") or txn_data.get("orderReference", "")
        if reference:
            txn = await billing_repo.find_transaction_by_reference(reference)
            if txn and txn.status == "pending":
                await billing_repo.mark_transaction_failed(txn.id)
                logger.info("Transaction %s marked failed", txn.id)

    elif event_type == "virtual_account.funded":
        account_ref = data.get("accountRef", "")
        txn_data = data.get("transaction", data)
        amount_received = txn_data.get("amountReceived", txn_data.get("transactionAmount", 0))
        logger.info(
            "Virtual account funded: ref=%s amount=%s",
            account_ref,
            amount_received,
        )

        invoice = await billing_repo.find_invoice_by_account_ref(account_ref)
        if not invoice:
            logger.error("No invoice found for virtual account ref=%s", account_ref)
            return Response(status_code=200)

        va_reference = f"va_{account_ref}"
        txn = await billing_repo.find_transaction_by_reference(va_reference)
        if txn and txn.status == "successful":
            return Response(status_code=200)

        amount_kobo = (
            int(amount_received * 100)
            if amount_received and amount_received < 1_000_000
            else int(amount_received)
        )
        if txn:
            await billing_repo.mark_transaction_successful(
                txn.id,
                channel="bank_transfer",
                fee_kobo=0,
                net_kobo=amount_kobo or txn.amount_cents,
            )
        else:
            created = await billing_repo.create_payment_transaction(
                store_id=invoice.store_id,
                order_id=invoice.order_id,
                reference=va_reference,
                customer=invoice.customer_name,
                amount_cents=amount_kobo or invoice.total,
                type="payment",
                payment_method="Nomba",
                status="pending",
                channel="bank_transfer",
                customer_email=invoice.customer_email or "",
                customer_phone=invoice.customer_phone or "",
            )
            await billing_repo.mark_transaction_successful(
                created.id,
                channel="bank_transfer",
                fee_kobo=0,
                net_kobo=amount_kobo or invoice.total,
            )

        if invoice.status != "paid":
            await billing_repo.mark_invoice_paid(invoice.id)
        await billing_repo.update_order_payment(invoice.order_id, "paid", "Nomba")
        logger.info("Invoice %s paid via virtual account transfer", invoice.id)

    else:
        logger.info("Unhandled Nomba webhook event: %s", event_type)

    return Response(status_code=200)
