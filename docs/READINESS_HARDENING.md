# Base readiness hardening

This is the FIRST hardening checkpoint. See BASE_HISTORY_PILOT.md for the
subsequent implemented history stage and current limitations.

Status: staged locally on fix/base-readiness, not a production deployment.

The API now fails closed for low-risk claims: ordinary ERC-20 metadata is not
security coverage. The current pipeline reports INSUFFICIENT_DATA / null rug score
until real security coverage is implemented. Market warnings remain independent.
Clients must accept null scores and inspect coverage, not render null as zero.

## Implemented

- Base/chain-ID and deployed-code checks before a scan.
- Blockscout creation lookup cross-checked with RPC transaction and receipt.
- Direct contract creation identity only; factory tokens return
  FACTORY_TRACE_REQUIRED with no asserted deployer. Originating user is not inferred.
- Explicit NOT_CHECKED history, bytecode, holder and simulation coverage.
- Legacy classifier-derived creator_rug_rate no longer used by the API risk engine.
- Historical database scores excluded from current decisions; memory cache is
  version/network/TTL checked. Historical feed is not a fresh assessment.
- Incorrect V2-style factory market fallback disabled. Market outages yield UNKNOWN.
- Unknown rug scores cannot be published via registry/module publication helpers.

## Live verification, September 6, 2026

Read-only local scan_token calls against public RPC and Blockscout:

- USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913:
  VERIFIED_DIRECT_CREATION, deployer 0x6aAFF8af0ae8017725312C388bA3745dfE91185B,
  creation tx 0x8aa214f98bcf2984add809d10232135cccc4d6ab97d8477e66475d8bf68def34,
  block 2797221. Rug score null, history NOT_CHECKED.
- AERO 0x940181a94A35A4569E4529A3CDfB74e38FD98631:
  VERIFIED_DIRECT_CREATION, deployer 0xe83f922C34A1962e9aE9F52B59e18239764f2818,
  creation tx 0x5727b7b346eb94d6f139e10e7ac922158dacd84f5d2844c01cf815b29d9ba58c,
  block 3200550. Rug score null, history NOT_CHECKED.

These are smoke checks, not a statistically meaningful accuracy benchmark.
Creation identity does not establish safety, current ownership or human identity.

## Remaining before a paid repeat-deployer pilot

Factory trace verification; independently labeled Base malicious/benign holdout
examples; durable deduplicated confirmed incident history; measured false positive
and false negative rates; provider coverage/latency benchmarks. The separate legacy
collector and main scoring-engine still require migration and must not be sold as
confirmed historical rug evidence. Memory Firewall Base adapter is not added here.

Before deployment, verify UI null-score rendering, eliminate old low-risk marketing
claims, and test the full deployed integration. Production was intentionally left
unchanged. No keys, paid calls, notifications or onchain writes were used in tests.

Run: python -m pytest tests -q
