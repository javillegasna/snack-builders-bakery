import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest_asyncio
from httpx import AsyncClient

from app.core.clock import SystemClock
from app.kitchen.engine import KitchenEngine
from app.kitchen.router import get_engine
from app.main import app


@pytest_asyncio.fixture
async def pay_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    engine = KitchenEngine(SystemClock())
    app.dependency_overrides[get_engine] = lambda: engine
    yield client


async def _placed_order(
    client: AsyncClient, *, priority: str = "walk_in"
) -> dict[str, Any]:
    item = await client.post(
        "/menu/items",
        json={"name": "Choc Cookie", "category": "cookie", "price": "3.50"},
    )
    assert item.status_code == 201, item.text
    item_id = item.json()["id"]
    order = await client.post(
        "/orders",
        json={
            "items": [{"menu_item_id": item_id, "quantity": 2}],
            "priority_level": priority,
        },
    )
    assert order.status_code == 201, order.text
    body: dict[str, Any] = order.json()
    return body


async def test_pay_confirms_and_queues(pay_client: AsyncClient) -> None:
    order = await _placed_order(pay_client)
    resp = await pay_client.post(
        f"/orders/{order['id']}/payment", json={"method": "cash"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["method"] == "cash"
    assert body["status"] == "confirmed"
    assert Decimal(str(body["amount"])) == Decimal("7.00")

    tracked = await pay_client.get(f"/orders/{order['id']}")
    assert tracked.json()["status"] == "queued"
    assert tracked.json()["estimated_ready_time"] is not None


async def test_pay_with_card(pay_client: AsyncClient) -> None:
    order = await _placed_order(pay_client)
    resp = await pay_client.post(
        f"/orders/{order['id']}/payment", json={"method": "card"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["method"] == "card"
    assert resp.json()["status"] == "confirmed"


async def test_pay_enqueues_into_kitchen(pay_client: AsyncClient) -> None:
    order = await _placed_order(pay_client)
    await pay_client.post(f"/orders/{order['id']}/payment", json={"method": "cash"})
    status = await pay_client.get("/kitchen/status")
    trays = [
        tray
        for oven in status.json()["ovens"]
        for tray in oven["trays"]
        if tray["order_id"] == order["id"]
    ]
    assert trays, "order should occupy a kitchen tray after payment"


async def test_pay_unknown_order_404(pay_client: AsyncClient) -> None:
    resp = await pay_client.post(
        f"/orders/{uuid.uuid4()}/payment", json={"method": "cash"}
    )
    assert resp.status_code == 404


async def test_pay_twice_conflicts(pay_client: AsyncClient) -> None:
    order = await _placed_order(pay_client)
    first = await pay_client.post(
        f"/orders/{order['id']}/payment", json={"method": "cash"}
    )
    assert first.status_code == 201
    second = await pay_client.post(
        f"/orders/{order['id']}/payment", json={"method": "cash"}
    )
    assert second.status_code == 409


async def _menu_item(client: AsyncClient) -> str:
    item = await client.post(
        "/menu/items",
        json={"name": "VIP Cookie", "category": "cookie", "price": "1.00"},
    )
    assert item.status_code == 201, item.text
    item_id: str = item.json()["id"]
    return item_id


async def _place_and_pay(
    client: AsyncClient, item_id: str, *, quantity: int, priority: str = "walk_in"
) -> str:
    placed = await client.post(
        "/orders",
        json={
            "items": [{"menu_item_id": item_id, "quantity": quantity}],
            "priority_level": priority,
        },
    )
    assert placed.status_code == 201, placed.text
    order_id: str = placed.json()["id"]
    paid = await client.post(f"/orders/{order_id}/payment", json={"method": "cash"})
    assert paid.status_code == 201, paid.text
    return order_id


async def _eta(client: AsyncClient, order_id: str) -> datetime:
    body = (await client.get(f"/orders/{order_id}")).json()
    return datetime.fromisoformat(body["estimated_ready_time"])


async def test_vip_payment_pushes_back_queued_order(pay_client: AsyncClient) -> None:
    item_id = await _menu_item(pay_client)
    # fill all 6 oven slots, then queue 6 more walk-in units behind them
    await _place_and_pay(pay_client, item_id, quantity=6)
    queued = await _place_and_pay(pay_client, item_id, quantity=6)
    before = await _eta(pay_client, queued)

    # a VIP order jumps the wait queue, delaying the queued walk-in order
    await _place_and_pay(pay_client, item_id, quantity=1, priority="vip")
    after = await _eta(pay_client, queued)

    assert after > before


async def test_invalid_method_rejected(pay_client: AsyncClient) -> None:
    order = await _placed_order(pay_client)
    resp = await pay_client.post(
        f"/orders/{order['id']}/payment", json={"method": "bitcoin"}
    )
    assert resp.status_code == 422
