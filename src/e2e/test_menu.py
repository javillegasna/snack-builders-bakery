import httpx


def test_menu_lists(client: httpx.Client) -> None:
    resp = client.get("/menu")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_menu_create_then_delete(client: httpx.Client) -> None:
    payload = {"name": "E2E Croissant", "category": "pastry", "price": "3.50"}
    created = client.post("/menu/items", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert item["name"] == payload["name"]

    item_id = item["id"]
    assert client.get("/menu").status_code == 200
    assert client.delete(f"/menu/items/{item_id}").status_code == 204
