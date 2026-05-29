import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import SystemClock
from app.kitchen.engine import KitchenEngine
from app.kitchen.router import get_engine
from app.main import app
from app.orders.models import Order, OrderPriority, OrderStatus


@pytest_asyncio.fixture
async def order_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    engine = KitchenEngine(SystemClock())
    app.dependency_overrides[get_engine] = lambda: engine
    yield client


async def _create_menu_item(
    client: AsyncClient,
    *,
    name: str = "Choc Cookie",
    category: str = "cookie",
    price: str = "3.50",
    available: bool = True,
) -> str:
    resp = await client.post(
        "/menu/items",
        json={
            "name": name,
            "category": category,
            "price": price,
            "available": available,
        },
    )
    assert resp.status_code == 201, resp.text
    item_id: str = resp.json()["id"]
    return item_id


async def test_place_order_returns_ticket(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client, price="3.50")
    resp = await order_client.post(
        "/orders",
        json={"items": [{"menu_item_id": item_id, "quantity": 2}]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending_payment"
    assert body["priority_level"] == "walk_in"
    assert Decimal(str(body["total_price"])) == Decimal("7.00")
    assert len(body["items"]) == 1
    assert body["items"][0]["menu_item_id"] == item_id
    assert body["items"][0]["quantity"] == 2
    assert Decimal(str(body["items"][0]["unit_price"])) == Decimal("3.50")
    assert body["estimated_ready_time"] is not None
    eta = datetime.fromisoformat(body["estimated_ready_time"])
    placed = datetime.fromisoformat(body["placed_at"])
    assert eta > placed


async def test_place_order_with_vip_priority(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client)
    resp = await order_client.post(
        "/orders",
        json={
            "items": [{"menu_item_id": item_id, "quantity": 1}],
            "priority_level": "vip",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["priority_level"] == "vip"


async def test_get_order_tracks_placed_order(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client)
    placed = await order_client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    order_id = placed.json()["id"]
    resp = await order_client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == order_id
    assert body["status"] == "pending_payment"
    assert len(body["items"]) == 1


async def test_get_unknown_order_returns_404(order_client: AsyncClient) -> None:
    resp = await order_client.get(f"/orders/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_empty_items_rejected(order_client: AsyncClient) -> None:
    resp = await order_client.post("/orders", json={"items": []})
    assert resp.status_code == 422


async def test_zero_quantity_rejected(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client)
    resp = await order_client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 0}]}
    )
    assert resp.status_code == 422


async def test_unknown_menu_item_rejected(order_client: AsyncClient) -> None:
    resp = await order_client.post(
        "/orders",
        json={"items": [{"menu_item_id": str(uuid.uuid4()), "quantity": 1}]},
    )
    assert resp.status_code == 422


async def test_unavailable_menu_item_rejected(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client, available=False)
    resp = await order_client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert resp.status_code == 422


async def test_deleting_referenced_menu_item_conflicts(
    order_client: AsyncClient,
) -> None:
    item_id = await _create_menu_item(order_client)
    placed = await order_client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    assert placed.status_code == 201
    resp = await order_client.delete(f"/menu/items/{item_id}")
    assert resp.status_code == 409


async def _seed_ready_order(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    order_id = uuid.uuid4()
    async with sessionmaker() as session:
        session.add(
            Order(
                id=order_id,
                priority_level=OrderPriority.WALK_IN,
                status=OrderStatus.READY,
                total_price=Decimal("3.50"),
                placed_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            )
        )
        await session.commit()
    return order_id


async def test_pickup_completes_ready_order(
    order_client: AsyncClient,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    order_id = await _seed_ready_order(db_sessionmaker)
    resp = await order_client.post(f"/orders/{order_id}/pickup")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


async def test_pickup_unknown_order_returns_404(order_client: AsyncClient) -> None:
    resp = await order_client.post(f"/orders/{uuid.uuid4()}/pickup")
    assert resp.status_code == 404


async def test_pickup_non_ready_order_conflicts(order_client: AsyncClient) -> None:
    item_id = await _create_menu_item(order_client)
    placed = await order_client.post(
        "/orders", json={"items": [{"menu_item_id": item_id, "quantity": 1}]}
    )
    order_id = placed.json()["id"]  # still pending_payment
    resp = await order_client.post(f"/orders/{order_id}/pickup")
    assert resp.status_code == 409
