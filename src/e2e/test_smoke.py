import httpx


def test_health(client: httpx.Client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready(client: httpx.Client) -> None:
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_menu_lists(client: httpx.Client) -> None:
    resp = client.get("/menu")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_kitchen_status_shape(client: httpx.Client) -> None:
    resp = client.get("/kitchen/status")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ovens"]) == 2
    assert all(len(oven["trays"]) == 3 for oven in body["ovens"])
    assert isinstance(body["queue"], list)


def test_menu_create_then_delete(client: httpx.Client) -> None:
    payload = {"name": "E2E Croissant", "category": "pastry", "price": "3.50"}
    created = client.post("/menu/items", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert item["name"] == payload["name"]

    item_id = item["id"]
    assert client.get("/menu").status_code == 200
    assert client.delete(f"/menu/items/{item_id}").status_code == 204
