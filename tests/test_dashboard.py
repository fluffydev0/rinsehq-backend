from datetime import datetime, timezone

from tests.helpers import signup_and_token


def _create_and_finalize(client, headers, status: str) -> None:
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Customer"},
            "lineItems": [{"name": "Wash", "quantity": 1, "unitPrice": 100000, "amount": 100000}],
            "total": 100000,
            "subtotal": 100000,
        },
    )
    order_id = create.json()["data"]["order"]["id"]
    client.post(f"/v1/orders/{order_id}/finalize", headers=headers)
    if status != "pending":
        client.patch(
            f"/v1/orders/{order_id}",
            headers=headers,
            json={"status": status},
        )


def test_dashboard_summary(client):
    headers = signup_and_token(client, "dash@example.com")
    for status in ("active", "pending", "completed"):
        _create_and_finalize(client, headers, status)

    response = client.get("/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["activeOrders"] >= 0
    assert data["pendingOrders"] >= 0
    assert data["completedOrders"] >= 0
    assert "draftOrders" in data
