from datetime import datetime, timezone

import pytest


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "orders@example.com", "password": "password123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "orders@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_orders_crud(client, auth_headers):
    now = datetime.now(timezone.utc).isoformat()
    create = client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={
            "type": "mobile_app",
            "customer": "Jane Doe",
            "amount_cents": 1500000,
            "status": "active",
            "order_date": now,
            "delivery_date": now,
            "delivery_mode": "Pickup & delivery",
        },
    )
    assert create.status_code == 201
    order_id = create.json()["id"]
    assert create.json()["customer"] == "Jane Doe"
    assert create.json()["amount_display"] == "N15,000"

    listing = client.get("/api/v1/orders", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert detail.status_code == 200

    update = client.patch(
        f"/api/v1/orders/{order_id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "completed"

    filtered = client.get("/api/v1/orders?status=completed", headers=auth_headers)
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1


def test_orders_require_auth(client):
    response = client.get("/api/v1/orders")
    assert response.status_code == 401


def test_get_order_not_found(client, auth_headers):
    response = client.get("/api/v1/orders/missing-id", headers=auth_headers)
    assert response.status_code == 404
