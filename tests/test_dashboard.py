from datetime import datetime, timezone

import pytest


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "dash@example.com", "password": "password123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "dash@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_summary(client, auth_headers):
    now = datetime.now(timezone.utc).isoformat()
    for status in ("active", "pending", "completed"):
        client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "type": "offline",
                "customer": "Customer",
                "amount_cents": 100000,
                "status": status,
                "order_date": now,
                "delivery_date": now,
                "delivery_mode": "Pickup only",
            },
        )

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["active"] == 1
    assert data["pending"] == 1
    assert data["completed"] == 1
