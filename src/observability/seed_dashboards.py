"""Seed OpenObserve dashboards from the JSON files in ./dashboards.

Idempotent: a dashboard with the same title is deleted and recreated.

Env:
  O2_BASE_URL   (default http://localhost:5080)
  O2_ORG        (default default)
  O2_FOLDER     (default default)
  Credentials, either:
    O2_USER / O2_PASSWORD
  or fall back to:
    ZO_ROOT_USER_EMAIL / ZO_ROOT_USER_PASSWORD

Run: uv run python src/observability/seed_dashboards.py
"""

import base64
import json
import os
import sys
from pathlib import Path

import httpx

DASHBOARDS_DIR = Path(__file__).parent / "dashboards"


def _auth_header() -> str:
    user = os.environ.get("O2_USER") or os.environ.get("ZO_ROOT_USER_EMAIL")
    password = os.environ.get("O2_PASSWORD") or os.environ.get("ZO_ROOT_USER_PASSWORD")
    if not user or not password:
        sys.exit(
            "Missing credentials: set O2_USER/O2_PASSWORD or "
            "ZO_ROOT_USER_EMAIL/ZO_ROOT_USER_PASSWORD."
        )
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


def _existing_by_title(client: httpx.Client, org: str) -> dict[str, str]:
    resp = client.get(f"/api/{org}/dashboards")
    resp.raise_for_status()
    result: dict[str, str] = {}
    for item in resp.json().get("dashboards", []):
        for version in ("v5", "v4", "v3", "v2", "v1"):
            body = item.get(version)
            if body and body.get("title"):
                result[body["title"]] = body["dashboardId"]
                break
    return result


def main() -> None:
    base_url = os.environ.get("O2_BASE_URL", "http://localhost:5080")
    org = os.environ.get("O2_ORG", "default")
    folder = os.environ.get("O2_FOLDER", "default")

    files = sorted(DASHBOARDS_DIR.glob("*.json"))
    if not files:
        sys.exit(f"No dashboard JSON files in {DASHBOARDS_DIR}")

    headers = {"Authorization": _auth_header(), "Content-Type": "application/json"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=15.0) as client:
        existing = _existing_by_title(client, org)
        for path in files:
            dashboard = json.loads(path.read_text())
            title = dashboard["title"]
            if title in existing:
                client.delete(
                    f"/api/{org}/dashboards/{existing[title]}",
                    params={"folder": folder},
                ).raise_for_status()
            resp = client.post(
                f"/api/{org}/dashboards",
                params={"folder": folder},
                content=json.dumps(dashboard),
            )
            resp.raise_for_status()
            print(f"seeded: {title}  ({path.name})")

    print(f"done -> {base_url} org={org} folder={folder}")


if __name__ == "__main__":
    main()
