import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from api import server
from chains.base.history import IncidentStore, history_decision

TOKEN = "0x" + "1" * 40
ACTOR = "0x" + "2" * 40
OTHER = "0x" + "3" * 40
IDENTITY = {"status": "VERIFIED_DIRECT_CREATION", "deployer": ACTOR}


@pytest.fixture
def store(tmp_path):
    s = IncidentStore(tmp_path / "history.db")
    s.initialize()
    return s


def event():
    # Synthetic verified-event fixture; not evidence of real-world accuracy.
    return {"verification": "RPC_VERIFIED_CURATED_INCIDENT", "chain_id": 8453,
            "deployer": ACTOR, "token": TOKEN}


def test_persistence_deduplication_and_repeat(store):
    key = store.add_verified(event())
    assert store.add_verified(event()) == key
    fresh = IncidentStore(store.path)
    assert len(fresh.lookup(8453, ACTOR.upper())) == 1
    assert history_decision(IDENTITY, TOKEN, fresh)["reason_code"] == "KNOWN_REVIEWED_INCIDENT"
    assert history_decision(IDENTITY, OTHER, fresh)["reason_code"] == "DEPLOYER_REVIEWED_INCIDENT_HISTORY"


def test_restart_actual_process(store):
    store.add_verified(event())
    code = "from chains.base.history import IncidentStore; import sys; print(len(IncidentStore(sys.argv[1]).lookup(8453, sys.argv[2])))"
    output = subprocess.check_output([sys.executable, "-c", code, str(store.path), ACTOR], text=True)
    assert output.strip() == "1"


def test_missing_and_corrupt_memory_fail_closed(tmp_path):
    missing = IncidentStore(tmp_path / "missing.db")
    assert history_decision(IDENTITY, TOKEN, missing)["decision"] == "MEMORY_REQUIRED"
    assert not missing.path.exists()
    missing.path.write_bytes(b"not sqlite")
    assert history_decision(IDENTITY, TOKEN, missing)["decision"] == "MEMORY_REQUIRED"


def test_isolation_and_no_false_allow(store):
    store.add_verified(event())
    assert history_decision({**IDENTITY, "deployer": OTHER}, TOKEN, store)["decision"] == "UNKNOWN"
    assert history_decision(IDENTITY, TOKEN, store, 84532)["decision"] == "UNKNOWN"
    assert history_decision({"status": "UNKNOWN"}, TOKEN, store)["decision"] == "UNKNOWN"


def test_tamper_fails_closed(store):
    store.add_verified(event())
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE incidents SET body='{}'")
    assert history_decision(IDENTITY, TOKEN, store)["decision"] == "MEMORY_REQUIRED"


def test_no_predictions_imported(store):
    with pytest.raises(ValueError):
        store.add_verified({"verification": "DANGER", "chain_id": 8453})


def test_deleted_memory_not_bypassed_by_api_cache(store, monkeypatch):
    monkeypatch.setenv("BASE_HISTORY_DB", str(store.path))
    monkeypatch.setenv("RUGBUSTER_NETWORK", "base")
    store.add_verified(event())
    report = {"identity": IDENTITY, "risk_engine": server.RISK_ENGINE_VERSION, "network": "Base Mainnet"}
    server.put_cached_report(TOKEN, report)
    assert server.get_cached_report(TOKEN)["history_decision"]["decision"] == "BLOCK"
    store.path.unlink()
    assert server.get_cached_report(TOKEN)["history_decision"]["decision"] == "MEMORY_REQUIRED"


def test_deterministic_hash(store):
    store.add_verified(event())
    a = history_decision(IDENTITY, TOKEN, store)
    b = history_decision(IDENTITY, TOKEN, IncidentStore(store.path))
    assert a["decision_hash"] == b["decision_hash"]
    assert a["decision_hash"] != history_decision(IDENTITY, OTHER, store)["decision_hash"]
