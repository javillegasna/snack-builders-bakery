import uuid

from httpx import AsyncClient


async def test_create_and_list_menu(client: AsyncClient) -> None:
    resp = await client.post(
        "/menu/items",
        json={"name": "Choc Cookie", "category": "cookie", "price": "2.50"},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Choc Cookie"
    assert created["bake_seconds"] == 300

    listing = await client.get("/menu")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [created["id"]]


async def test_update_hides_unavailable_from_public_menu(client: AsyncClient) -> None:
    created = await client.post(
        "/menu/items",
        json={"name": "Baguette", "category": "bread", "price": "3.00"},
    )
    item_id = created.json()["id"]

    updated = await client.patch(
        f"/menu/items/{item_id}", json={"price": "3.50", "available": False}
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "3.50"
    assert updated.json()["available"] is False

    listing = await client.get("/menu")
    assert listing.json() == []


async def test_delete_item(client: AsyncClient) -> None:
    created = await client.post(
        "/menu/items",
        json={"name": "Tart", "category": "pastry", "price": "4.00"},
    )
    item_id = created.json()["id"]

    deleted = await client.delete(f"/menu/items/{item_id}")
    assert deleted.status_code == 204

    missing = await client.patch(f"/menu/items/{item_id}", json={"price": "5.00"})
    assert missing.status_code == 404


async def test_update_missing_returns_404(client: AsyncClient) -> None:
    resp = await client.patch(f"/menu/items/{uuid.uuid4()}", json={"price": "1.00"})
    assert resp.status_code == 404


async def test_oversized_price_is_rejected_not_500(client: AsyncClient) -> None:
    resp = await client.post(
        "/menu/items",
        json={"name": "Gold Loaf", "category": "bread", "price": "1000000000.00"},
    )
    assert resp.status_code == 422


async def test_name_with_null_byte_is_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/menu/items",
        json={"name": "bad\x00name", "category": "bread", "price": "2.00"},
    )
    assert resp.status_code == 422


async def test_patch_null_price_is_ignored(client: AsyncClient) -> None:
    created = await client.post(
        "/menu/items",
        json={"name": "Roll", "category": "bread", "price": "2.00"},
    )
    item_id = created.json()["id"]

    updated = await client.patch(
        f"/menu/items/{item_id}", json={"price": None, "available": False}
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "2.00"
    assert updated.json()["available"] is False
