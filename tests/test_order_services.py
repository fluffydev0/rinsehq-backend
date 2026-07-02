from tests.helpers import signup_and_token


def _create_service(client, headers, name="Wash & Fold", unit_price=350000):
    response = client.post(
        "/v1/services",
        headers=headers,
        json={
            "name": name,
            "category": "wash",
            "laundryMode": "Wash system",
            "unitPrice": unit_price,
            "pricingUnit": "per_load",
            "turnaroundHours": 24,
            "status": "active",
            "description": "Test service",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_create_order_from_catalog_service(client):
    headers = signup_and_token(client, "svc-order@example.com")
    service = _create_service(client, headers)

    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Catalog Customer", "email": "cat@example.com"},
            "lineItems": [{"serviceId": service["id"], "quantity": 2}],
            "orderType": "drop-off",
        },
    )
    assert create.status_code == 201, create.text
    order = create.json()["data"]["order"]
    assert order["status"] == "draft"
    assert len(order["lineItems"]) == 1

    line = order["lineItems"][0]
    assert line["serviceId"] == service["id"]
    assert line["name"] == service["name"]
    assert line["unitPrice"] == service["unitPrice"]
    assert line["quantity"] == 2
    assert line["amount"] == service["unitPrice"] * 2
    assert order["subtotal"] == service["unitPrice"] * 2
    assert order["vat"] > 0
    assert order["total"] == order["subtotal"] + order["vat"]


def test_finalize_increments_service_orders_count(client):
    headers = signup_and_token(client, "svc-count@example.com")
    service = _create_service(client, headers, name="Dry Clean", unit_price=500000)

    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Count Customer"},
            "lineItems": [{"serviceId": service["id"], "quantity": 1}],
        },
    )
    order_id = create.json()["data"]["order"]["id"]

    before = client.get(f"/v1/services/{service['id']}", headers=headers).json()["data"]
    assert before["ordersCount"] == 0

    finalize = client.post(f"/v1/orders/{order_id}/finalize", headers=headers)
    assert finalize.status_code == 200

    after = client.get(f"/v1/services/{service['id']}", headers=headers).json()["data"]
    assert after["ordersCount"] == 1


def test_create_order_rejects_unknown_service(client):
    headers = signup_and_token(client, "svc-bad@example.com")
    response = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Bad Service"},
            "lineItems": [{"serviceId": "SRV-MISSING", "quantity": 1}],
        },
    )
    assert response.status_code == 404
    assert "Service not found" in response.json()["error"]


def test_create_order_rejects_inactive_service(client):
    headers = signup_and_token(client, "svc-inactive@example.com")
    service = _create_service(client, headers, name="Paused Service")
    client.patch(
        f"/v1/services/{service['id']}/status",
        headers=headers,
        json={"status": "inactive"},
    )

    response = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Inactive Service"},
            "lineItems": [{"serviceId": service["id"], "quantity": 1}],
        },
    )
    assert response.status_code == 400
    assert "not active" in response.json()["error"]


def test_manual_line_item_still_supported(client):
    headers = signup_and_token(client, "svc-manual@example.com")
    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Manual Customer"},
            "lineItems": [
                {
                    "name": "Custom alteration",
                    "quantity": 1,
                    "unitPrice": 250000,
                    "amount": 250000,
                }
            ],
        },
    )
    assert create.status_code == 201
    line = create.json()["data"]["order"]["lineItems"][0]
    assert line["serviceId"] == ""
    assert line["name"] == "Custom alteration"


def test_update_order_line_items_from_catalog(client):
    headers = signup_and_token(client, "svc-update@example.com")
    wash = _create_service(client, headers, name="Wash", unit_price=200000)
    fold = _create_service(client, headers, name="Fold", unit_price=100000)

    create = client.post(
        "/v1/orders",
        headers=headers,
        json={
            "customer": {"name": "Update Customer"},
            "lineItems": [{"serviceId": wash["id"], "quantity": 1}],
        },
    )
    order_id = create.json()["data"]["order"]["id"]

    update = client.patch(
        f"/v1/orders/{order_id}",
        headers=headers,
        json={"lineItems": [{"serviceId": fold["id"], "quantity": 3}]},
    )
    assert update.status_code == 200
    lines = update.json()["data"]["lineItems"]
    assert len(lines) == 1
    assert lines[0]["serviceId"] == fold["id"]
    assert lines[0]["amount"] == fold["unitPrice"] * 3
