from __future__ import annotations

from fastapi.testclient import TestClient

# Ensure app package imports resolve when running from repo root
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src/app").resolve()))

from api import app  # noqa: E402


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
