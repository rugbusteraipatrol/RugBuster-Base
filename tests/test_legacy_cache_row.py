"""A stored row the label cannot be derived from is passed over, not served.

Base cbBTC, 2026-09-11: /score returned label UNKNOWN from postgres_cache with
"0% of the checks ran". The row came from the older collector and carried a
risk percent but no rug_status, which is what the public label is read from.
A live scan of the same address answered WARN.
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

LEGACY_ROW = {
    "contract_address": CBBTC,
    "token_name": "Coinbase Wrapped BTC",
    "token_symbol": "cbBTC",
    "rugbuster_BASE_score": 46,
    "rugbuster_BASE_reasons": ["Bytecode backdoor risk 40/100", "Upgradeable proxy contract"],
}

LIVE_REPORT = {
    "address": CBBTC,
    "token_name": "Coinbase Wrapped BTC",
    "symbol": "cbBTC",
    "rug_status": "LOW",
    "speculation_status": "ELEVATED",
    "risk_percent": 12,
}


class _Cursor:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return _Cursor(self.row)


@pytest.fixture()
def server(monkeypatch):
    monkeypatch.setenv("RUGBUSTER_API_KEY", "")
    import api.server as srv
    importlib.reload(srv)
    srv.SCAN_CACHE.clear()
    srv.app.config.update(TESTING=True)
    return srv


def _with_database_row(server, monkeypatch, row):
    fake = mock.Mock()
    fake.connect = lambda *a, **k: _Connection((row,) if row is not None else None)
    monkeypatch.setattr(server, "psycopg2", fake)
    monkeypatch.setattr(server, "DATABASE_URL", "postgres://test")


def test_a_row_without_rug_status_is_not_served(server, monkeypatch):
    _with_database_row(server, monkeypatch, LEGACY_ROW)
    assert server.lookup_cached_score(CBBTC) is None


def test_score_falls_through_to_a_live_scan_instead_of_unknown(server, monkeypatch):
    _with_database_row(server, monkeypatch, LEGACY_ROW)
    with mock.patch.object(server, "scan_token", return_value=dict(LIVE_REPORT)) as scan:
        body = server.app.test_client().get(f"/score?address={CBBTC}").get_json()
    scan.assert_called_once()
    assert body["source"] == "live_score"
    assert body["label"] != "UNKNOWN"


def test_a_row_with_rug_status_is_still_served_from_cache(server, monkeypatch):
    _with_database_row(server, monkeypatch, {**LEGACY_ROW, "rug_status": "LOW", "speculation_status": "LOW"})
    with mock.patch.object(server, "scan_token") as scan:
        body = server.app.test_client().get(f"/score?address={CBBTC}").get_json()
    scan.assert_not_called()
    assert body["source"] == "postgres_cache"


def test_a_memory_cache_entry_without_rug_status_is_not_served(server, monkeypatch):
    server.put_cached_report(CBBTC, dict(LEGACY_ROW))
    monkeypatch.setattr(server, "DATABASE_URL", "")
    assert server.lookup_cached_score(CBBTC) is None
