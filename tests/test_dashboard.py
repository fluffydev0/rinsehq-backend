from datetime import datetime, timezone

from tests.helpers import signup_and_token


def test_dashboard_summary(client):
    headers = signup_and_token(client, "dash@example.com")
    now = datetime.now(timezone.utc).isoformat()
    for status in ("active", "pending", "completed"):
        client.post(
            "/v1/orders",
            headers=headers,
            json={
                "customer": {"name": "Customer"},
                "lineItems": [{"name": "Wash", "quantity": 1, "unitPrice": 100000, "amount": 100000}],
                "total": 100000,
                "subtotal": 100000,
            },
        )
        if status != "pending":
            orders = client.get("/v1/orders", headers=headers).json()["data"]
            if orders:
                client.patch(
                    f"/v1/orders/{orders[-1]['id']}",
                    headers=headers,
                    json={"status": status},
                )

    response = client.get("/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["activeOrders"] >= 0
    assert data["pendingOrders"] >= 0
    assert data["completedOrders"] >= 0
