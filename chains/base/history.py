"""Local curated incident journal. Classifier predictions are never incident input."""

import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def event_hash(event):
    return hashlib.sha256(canonical(event).encode()).hexdigest()


class IncidentStore:
    def __init__(self, path):
        self.path = Path(path).resolve()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, chain INTEGER NOT NULL, actor TEXT NOT NULL, token TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(chain, token, id))")

    def add_verified(self, event):
        if event.get("verification") != "RPC_VERIFIED_CURATED_INCIDENT" or event.get("chain_id") != 8453:
            raise ValueError("Only verified curated Base events can be stored")
        key = event_hash(event)
        # No HTTP write route exists. Only the local evidence-verification CLI writes.
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR IGNORE INTO incidents VALUES (?, ?, ?, ?, ?)",
                       (key, 8453, event["deployer"].lower(), event["token"].lower(), canonical(event)))
        return key

    def lookup(self, chain, actor):
        # Read-only open must not silently create a new empty database after deletion.
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)) as db:
            rows = db.execute("SELECT id, body FROM incidents WHERE chain=? AND actor=? ORDER BY id",
                              (chain, actor.lower())).fetchall()
        events = []
        for key, body in rows:
            event = json.loads(body)
            if event_hash(event) != key or event.get("deployer", "").lower() != actor.lower():
                raise ValueError("Incident journal integrity failure")
            events.append({"id": key, **event})
        return events


def history_decision(identity, token, store, chain=8453):
    base = {"decision": "MEMORY_REQUIRED", "reason_code": "HISTORY_UNAVAILABLE", "evidence": [],
            "policy_version": "base-reviewed-history-v1", "coverage": "CURATED_INCIDENTS_ONLY",
            "history_status": "UNAVAILABLE"}
    if identity.get("status") != "VERIFIED_DIRECT_CREATION" or not identity.get("deployer"):
        return {**base, "decision": "UNKNOWN", "reason_code": "IDENTITY_NOT_ATTRIBUTABLE", "history_status": "NOT_CHECKED"}
    try:
        events = store.lookup(chain, identity["deployer"])
    except (sqlite3.Error, ValueError, OSError, KeyError, TypeError):
        return base
    if not events:
        return {**base, "decision": "UNKNOWN", "reason_code": "NO_KNOWN_INCIDENT_NOT_PROOF_OF_SAFETY", "history_status": "CURATED_CHECKED"}
    same = any(e["token"].lower() == token.lower() for e in events)
    decision = {**base, "decision": "BLOCK", "reason_code": "KNOWN_REVIEWED_INCIDENT" if same else "DEPLOYER_REVIEWED_INCIDENT_HISTORY",
                "evidence": events, "history_status": "CURATED_CHECKED"}
    decision["decision_hash"] = event_hash({"chain": chain, "token": token.lower(),
        "deployer": identity["deployer"].lower(), "policy": base["policy_version"],
        "evidence": [e["id"] for e in events], "decision": "BLOCK"})
    return decision
