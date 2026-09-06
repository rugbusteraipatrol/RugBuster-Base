"""Small real-token smoke test, not a detection-accuracy benchmark."""

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.server import app

CASES = [
    ("BALD_reviewed_incident", "0x27D2DECb4bFC9C76F0309b8E88dec3a601Fe25a8", "BLOCK"),
    ("USDC_control_not_a_safety_label", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "UNKNOWN"),
    ("AERO_control_not_a_safety_label", "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "UNKNOWN"),
    ("Leet_pool_factory_attribution", "0xE96df8F5ef1A8790415068c798765b07D57643bd", "UNKNOWN"),
]


def main():
    results = []
    with app.test_client() as client:
        for name, address, expected in CASES:
            start = time.monotonic()
            response = client.post("/api/preflight", json={"chain": "base", "address": address})
            item = {"case": name, "elapsed_seconds": round(time.monotonic() - start, 3),
                    "http_status": response.status_code, "response": response.json,
                    "passed": response.status_code == 200 and response.json.get("decision") == expected}
            results.append(item)
            print(name, response.status_code, response.json.get("decision"), item["elapsed_seconds"])
    path = ROOT / "data/live-history-smoke.json"
    path.write_text(json.dumps({"checked_at": int(time.time()), "scope": "four-case live smoke, not a holdout benchmark",
                                "results": results}, indent=2), encoding="utf-8")
    print("Report:", path)
    if not all(r["passed"] for r in results):
        raise SystemExit("Live smoke failed; inspect provider/data failures before claiming readiness")


if __name__ == "__main__":
    main()
