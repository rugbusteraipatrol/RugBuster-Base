# Reviewed Base history pilot

## Scope

Working local vertical slice: token address -> verified direct creator -> persistent
curated incident lookup -> BLOCK / UNKNOWN / MEMORY_REQUIRED with evidence.
There is intentionally no ALLOW until independent security coverage supports it.
One curated incident is seeded, BALD. This is not a broad rug detector or a
measured commercial accuracy claim. Do not advertise all Base tokens as supported.

## Setup

Install requirements.txt plus pytest. From the repository root:

```sh
python scripts/verify_base_history.py --db data/base-reviewed-incidents.db
python -m pytest tests -q
python scripts/live_history_smoke.py
python -m api.server
```

The importer re-queries public Base RPC and Blockscout. It checks token creation,
transaction sender/success/canonical block, pool assets/factory registration,
LeetSwap Burn and Sync events, and >=90% quote-reserve removal in the selected burn.
The independent report is curator-reviewed, not automatically proven by its URL.
Local imports are trusted administrative operations. No public evidence-write route
is exposed. Evidence bodies are hashed and deduplicated, not cryptographically signed.

Use BASE_HISTORY_DB for a persistent volume path on deployment. Default path is
data/base-reviewed-incidents.db. Missing/corrupt storage fails closed. SQLite
connections close explicitly; a removed DB is not silently recreated on reads.
Incident evidence is immutable in this version. Retraction/versioned review support
is required before a larger dataset rollout; do not edit row JSON in place.

## Client integration

```http
POST /api/preflight
Content-Type: application/json

{"chain":"base","address":"0x27D2DECb4bFC9C76F0309b8E88dec3a601Fe25a8"}
```

- BLOCK: curated reviewed incident matched. Examine reason_code, evidence and decision_hash.
- UNKNOWN: identity not attributable, or no known incident in this limited dataset.
- MEMORY_REQUIRED: attributed identity, but history storage unavailable or invalid.
- HTTP 503 + UNKNOWN: provider/scan unavailable. Never execute on this result.

Endpoint does not sign, submit, or intercept transactions. The consuming application
must enforce its own stop/review behavior. Clients must not map null risk scores to 0.
The general market/rug report remains separate from incident-history policy.
The old scan API's publish/notify actions require BASE_ADMIN_TOKEN and matching
X-RugBuster-Admin-Token; leave publication disabled for the read-only pilot.

## Verified September 6, 2026

45 automated tests passed. Covers actual fresh Python process recall, deduplication,
cross-chain/actor isolation, corrupted/deleted memory, cache deletion bypass,
bad evidence, provider outages, and factory shared-identity isolation.

Live Flask endpoint requests, with real RPC/explorer/market data:

| Case | Result | Seconds |
| --- | --- | --- |
| BALD reviewed incident | BLOCK | 4.823 |
| USDC control | UNKNOWN | 6.522 |
| AERO control | UNKNOWN | 8.343 |
| LeetSwap pool factory creation | UNKNOWN | 4.261 |

This is a four-case smoke check, not a holdout benchmark. No precision/recall or
false-positive rate is claimed. These latencies are not a production SLA.

BALD: RPC verified removal of 6809.966019028490636295 WETH and remaining
375.867440111226050288 WETH in the selected burn, 9476 basis points of the
reconstructed WETH reserve (94.76%, rounded down). This is not necessarily the
total loss or total liquidity removal across the full incident.

- [Onchain transaction](https://base.blockscout.com/tx/0xd4fce790ac42a5a801bebb220adc2a6f9d9bf99985de6a824638a269c3e52ade)
- [Independent security report](https://www.fairyproof.com/img/researchImg/WR_31Jul-6Aug.pdf)

Factory CREATE/CREATE2 trace parsing is implemented and unit-tested. Public Base RPC
returned HTTP 403 for debug_traceTransaction; PublicNode reported method unavailable.
Live factory attribution therefore remains UNKNOWN. A trace-capable RPC and explicit
per-factory user attribution are still needed. Never blacklist all users of a factory.

## Before broader rollout

Independent held-out Base examples; real second-token repeat-deployer verification;
larger reviewed dataset; trace-capable RPC; evidence retraction; deployed UI null-score
QA; hosted authentication/rate limiting; production deployment and smoke verification.
Legacy collector/scoring-engine and Sibyl adapter are not migrated by this branch.
