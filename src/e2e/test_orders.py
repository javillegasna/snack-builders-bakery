import time

import httpx


def _wait_for_status(
    client: httpx.Client, order_id: str, target: str, timeout: float = 20.0
) -> str:
    deadline = time.monotonic() + timeout
    status = ""
    while time.monotonic() < deadline:
        status = client.get(f"/orders/{order_id}").json()["status"]
        if status == target:
            return status
        time.sleep(0.3)
    return status


def test_place_then_track_order(client: httpx.Client) -> None:
    created = client.post(
        "/menu/items",
        json={"name": "E2E Order Cookie", "category": "cookie", "price": "2.00"},
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    placed = client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 3}]}
    )
    assert placed.status_code == 201
    order = placed.json()
    assert order["status"] == "pending_payment"
    assert order["total_price"] in ("6.00", "6.0", 6.0, 6)
    assert order["estimated_ready_time"] is not None

    tracked = client.get(f"/orders/{order['id']}")
    assert tracked.status_code == 200
    assert tracked.json()["id"] == order["id"]


def test_pickup_unready_order_conflicts(client: httpx.Client) -> None:
    created = client.post(
        "/menu/items",
        json={"name": "E2E Pickup Cookie", "category": "cookie", "price": "2.00"},
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    placed = client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert placed.status_code == 201
    order_id = placed.json()["id"]  # pending_payment, not ready

    resp = client.post(f"/orders/{order_id}/pickup")
    assert resp.status_code == 409


def test_full_lifecycle_place_pay_bake_pickup(client: httpx.Client) -> None:
    # a fast test product (1s bake) makes the full lifecycle observable under the
    # real clock instead of waiting out a 5-minute cookie
    created = client.post(
        "/menu/items",
        json={
            "name": "E2E Instant Cookie",
            "category": "cookie",
            "price": "1.00",
            "bake_seconds": 1,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["bake_seconds"] == 1
    item_id = created.json()["id"]

    placed = client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert placed.status_code == 201
    order_id = placed.json()["id"]

    paid = client.post(f"/orders/{order_id}/payment", json={"method": "cash"})
    assert paid.status_code == 201
    assert paid.json()["status"] == "confirmed"

    assert _wait_for_status(client, order_id, "ready") == "ready"

    picked = client.post(f"/orders/{order_id}/pickup")
    assert picked.status_code == 200
    body = picked.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
