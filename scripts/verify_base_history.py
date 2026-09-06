"""Read-only blockchain verification, then local SQLite import. No signing."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web3 import Web3
from chains.base.history import IncidentStore
from chains.base.incident_verifier import verify_incident


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--rpc", default="https://mainnet.base.org")
    args = parser.parse_args()
    web3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={"timeout": 20}))
    candidates = json.loads((ROOT / "evidence/base-reviewed-candidates.json").read_text())
    events = [verify_incident(web3, candidate) for candidate in candidates]
    store = IncidentStore(args.db)
    store.initialize()
    for event in events:
        key = store.add_verified(event)
        print(json.dumps({"event_id": key, **event}, indent=2))


if __name__ == "__main__":
    main()
