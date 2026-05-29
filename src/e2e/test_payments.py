import httpx


def test_pay_then_queue_order(client: httpx.Client) -> None:
    created = client.post(
        "/menu/items",
        json={"name": "E2E Pay Cookie", "category": "cookie", "price": "2.50"},
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    placed = client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert placed.status_code == 201
    order_id = placed.json()["id"]

    paid = client.post(f"/orders/{order_id}/payment", json={"method": "card"})
    assert paid.status_code == 201
    assert paid.json()["status"] == "confirmed"

    tracked = client.get(f"/orders/{order_id}")
    assert tracked.json()["status"] == "queued"
