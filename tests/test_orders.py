from datetime import datetime, timezone

from tests.helpers import signup_and_token


def test_orders_crud(client):
    headers = signup_and_token(client, "orders@example.com")
    now = datetime.now(timezone.utc).isoformat()
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
    order = create.json()["data"]["order"]
    order_id = order["id"]
    assert order["customer"] == "Jane Doe"

    listing = client.get("/v1/orders", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    detail = client.get(f"/v1/orders/{order_id}", headers=headers)
    assert detail.status_code == 200

    update = client.patch(
        f"/v1/orders/{order_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["status"] == "completed"


def test_orders_require_auth(client):
    response = client.get("/v1/orders")
    assert response.status_code == 401


def test_get_order_not_found(client):
    headers = signup_and_token(client, "orders2@example.com")
    response = client.get("/v1/orders/missing-id", headers=headers)
    assert response.status_code == 404
