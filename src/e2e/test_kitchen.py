import httpx


def test_kitchen_status_shape(client: httpx.Client) -> None:
    resp = client.get("/kitchen/status")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ovens"]) == 2
    assert all(len(oven["trays"]) == 3 for oven in body["ovens"])
    assert isinstance(body["queue"], list)
