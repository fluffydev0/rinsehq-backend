from datetime import datetime, timezone

from tests.helpers import signup_and_token


def test_orders_crud(client):
    headers = signup_and_token(client, "orders@example.com")
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Jane Doe", "email": "jane@example.com", "phone": "+2348012345678"},
            "lineItems": [{"name": "Wash", "quantity": 1, "unitPrice": 1500000, "amount": 1500000}],
            "orderType": "drop-off",
            "total": 1500000,
            "subtotal": 1500000,
        },
    )
    assert create.status_code == 201
    payload = create.json()["data"]
    order = payload["order"]
    order_id = order["id"]
    assert order["customer"] == "Jane Doe"
    assert order["status"] == "draft"
    assert payload["invoice"] is None

    listing = client.get("/v1/orders?status=draft", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = client.get(f"/v1/orders/{order_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["data"]["lineItems"]) == 1

    update = client.patch(
        f"/v1/orders/{order_id}",
        headers=headers,
        json={"description": "Updated draft"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["description"] == "Updated draft"

    finalize = client.post(f"/v1/orders/{order_id}/finalize", headers=headers)
    assert finalize.status_code == 200
    finalized = finalize.json()["data"]
    assert finalized["order"]["status"] == "pending"
    assert finalized["invoice"] is not None
    assert finalized["invoice"]["total"] > 0
    assert "paymentLink" in finalized

    complete = client.patch(
        f"/v1/orders/{order_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert complete.status_code == 200
    assert complete.json()["data"]["status"] == "completed"


def test_orders_require_auth(client):
    response = client.get("/v1/orders")
    assert response.status_code == 401


def test_get_order_not_found(client):
    headers = signup_and_token(client, "orders2@example.com")
    response = client.get("/v1/orders/missing-id", headers=headers)
    assert response.status_code == 404


def test_finalize_requires_line_items(client):
    headers = signup_and_token(client, "orders3@example.com")
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={"customer": {"name": "Empty"}, "lineItems": [], "total": 0},
    )
    assert create.status_code == 400
    assert "line item" in create.json()["error"].lower()


def test_list_customers_without_search(client):
    headers = signup_and_token(client, "customers@example.com")
    client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Listed User", "email": "listed@example.com"},
            "lineItems": [{"name": "Wash", "quantity": 1, "unitPrice": 100000, "amount": 100000}],
            "total": 100000,
        },
    )
    response = client.get("/v1/customers", headers=headers)
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["data"]]
    assert "Listed User" in names
