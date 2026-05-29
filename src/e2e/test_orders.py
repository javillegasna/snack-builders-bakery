import httpx


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
