import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import rinsehq.infrastructure.di as di_module
from rinsehq.infrastructure.payments.nomba_client import CheckoutResult, NombaClient
from tests.helpers import signup_and_token


def test_nomba_verify_webhook_signature():
    secret = "test-webhook-secret"
    body = b'{"event_type":"payment_success","data":{}}'
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert NombaClient.verify_webhook(body, signature, secret) is True
    assert NombaClient.verify_webhook(body, "bad-signature", secret) is False


def test_nomba_webhook_payment_success(client, db):
    headers = signup_and_token(client, "nomba-pay@example.com")
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Nomba Customer", "email": "nomba@example.com"},
            "lineItems": [{"name": "Wash", "quantity": 1, "unitPrice": 100000, "amount": 100000}],
            "total": 100000,
            "subtotal": 100000,
        },
    )
    order_id = create.json()["data"]["order"]["id"]
    finalize = client.post(f"/v1/orders/{order_id}/finalize", headers=headers)
    invoice = finalize.json()["data"]["invoice"]
    invoice_id = invoice["id"]
    invoice_no = invoice["invoiceNo"]
    reference = f"rinse_inv_{invoice_no.replace('-', '_').lower()}"

    from rinsehq.infrastructure.db.models import InvoiceModel, TransactionModel

    inv_row = db.get(InvoiceModel, invoice_id)
    txn = TransactionModel(
        id="TXN-099",
        store_id=inv_row.store_id,
        order_id=order_id,
        reference=reference,
        customer="Nomba Customer",
        amount_cents=invoice["total"],
        type="payment",
        payment_method="Nomba",
        status="pending",
    )
    db.add(txn)
    db.commit()

    payload = {
        "event_type": "payment_success",
        "data": {
            "transaction": {
                "merchantTxRef": reference,
                "transactionAmount": invoice["total"],
                "fee": 100,
                "type": "card",
            }
        },
    }
    raw = json.dumps(payload).encode()

    response = client.post(
        "/v1/webhooks/nomba",
        content=raw,
        headers={"Content-Type": "application/json", "nomba-signature": "ignored-in-dev"},
    )
    assert response.status_code == 200

    db.expire_all()
    inv_row = db.get(InvoiceModel, invoice_id)
    assert inv_row.status == "paid"
    txn_row = db.query(TransactionModel).filter(TransactionModel.reference == reference).one()
    assert txn_row.status == "successful"


def test_pay_invoice_creates_pending_transaction(client, db):
    mock_client = AsyncMock()
    mock_client.create_checkout.return_value = CheckoutResult(
        checkout_url="https://checkout.nomba.com/test",
        order_reference="rinse_inv_inv_test1234",
    )
    previous = di_module._nomba_client
    di_module._nomba_client = mock_client

    headers = signup_and_token(client, "nomba-init@example.com")
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Pay Test", "email": "pay@example.com"},
            "lineItems": [{"name": "Dry Clean", "quantity": 1, "unitPrice": 50000, "amount": 50000}],
            "total": 50000,
            "subtotal": 50000,
        },
    )
    order_id = create.json()["data"]["order"]["id"]
    finalize = client.post(f"/v1/orders/{order_id}/finalize", headers=headers)
    invoice = finalize.json()["data"]["invoice"]
    invoice_id = invoice["id"]
    invoice_no = invoice["invoiceNo"]
    expected_ref = f"rinse_inv_{invoice_no.replace('-', '_').lower()}"
    mock_client.create_checkout.return_value = CheckoutResult(
        checkout_url="https://checkout.nomba.com/test",
        order_reference=expected_ref,
    )

    try:
        pay = client.post(
            f"/v1/invoices/{invoice_id}/pay",
            json={"callbackUrl": "http://localhost:5173/callback"},
        )
    finally:
        di_module._nomba_client = previous

    assert pay.status_code == 200
    data = pay.json()["data"]
    assert data["authorizationUrl"] == "https://checkout.nomba.com/test"
    assert data["reference"] == expected_ref

    from rinsehq.infrastructure.db.models import TransactionModel

    txn_row = (
        db.query(TransactionModel)
        .filter(TransactionModel.reference == expected_ref)
        .one()
    )
    assert txn_row.status == "pending"
    assert txn_row.payment_method == "Nomba"
