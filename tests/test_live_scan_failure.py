"""An unusable cache plus a failed live read is "the check failed", not "no token".

Before: /score answered 404 with the raw exception text. A 404 reads as "this
address is not a token", which a failed RPC or market read cannot establish.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "chains" / "base"))

CBBTC = "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
LEGACY_ROW = {"contract_address": CBBTC, "rugbuster_BASE_score": 46}


@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_API_KEY", "")
    import api.server as srv
    importlib.reload(srv)
    srv.SCAN_CACHE.clear()
    srv.app.config.update(TESTING=True)
    monkeypatch.setattr(srv, "DATABASE_URL", "")
    return srv


@pytest.mark.parametrize("cached", [None, LEGACY_ROW])
def test_failed_live_read_is_reported_as_a_failed_check(server, cached):
    if cached:
        server.put_cached_report(CBBTC, dict(cached))
    with mock.patch.object(server, "scan_token", side_effect=ConnectionError("rpc https://secret-host timed out")):
        response = server.app.test_client().get(f"/score?address={CBBTC}")
    body = response.get_json()
    assert response.status_code == 502
    assert body["ok"] is False
    assert body["error"] == "live_scan_failed"
    assert "not a finding about the token" in body["message"]
    assert body["detail"] == "ConnectionError"
    assert "secret-host" not in response.get_data(as_text=True)
    assert "label" not in body


def test_invalid_address_is_still_a_400(server):
    assert server.app.test_client().get("/score?address=nope").status_code == 400
