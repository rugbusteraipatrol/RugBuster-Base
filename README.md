# RugBuster Base

AI-powered EVM token scanner and on-chain risk attestation layer for Base mainnet.

## Live Links

- Public landing page: `https://rugbusteraipatrol.github.io/RugBuster-Base/`
- Base API: `https://base-api-production-6887.up.railway.app`
- Base RPC: `https://mainnet.base.org`
- Chain ID: `8453`
- Explorer: `https://basescan.org`
- Scanner contract: `0x5F30276B3A5079E088Ec3072884286de5a868355`
- Basescan contract page: `https://basescan.org/address/0x5F30276B3A5079E088Ec3072884286de5a868355`
- Basescan source verification: pending `BASESCAN_API_KEY`
- Live Base scan count: 218 confirmed `base_scans` rows as of 2026-07-07 07:16 UTC; use `/api/recent-scans?chain=base&limit=25` for live data.

This repo ports the existing RugBuster Avalanche/BNB EVM scanner architecture to Base. Stats in the landing page and README should only be updated after the collector has written real rows to the shared Postgres database.

## Base Runtime

The 24/7 worker is `chains/base/base_collector_v1.py`. It writes records to:

```txt
base_scans
```

Supported Base discovery sources:

- GeckoTerminal Base new pools and top pools
- Aerodrome PoolFactory: `0x420dd381b31aef6683db6b902084cb0ffece40da`
- Uniswap V3 Factory on Base: `0x33128a8fC17869897dcE68Ed026d694621f6FDfD`

Base quote/common assets:

- WETH: `0x4200000000000000000000000000000000000006`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- USDbC: `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA`
- AERO: `0x940181a94A35A4569E4529A3CDfB74e38FD98631`

## Environment

Copy `.env.example` to `.env` locally, or set Railway variables:

```txt
RUGBUSTER_NETWORK=base
BASE_RPC_URL=https://mainnet.base.org
BASE_RPC=https://mainnet.base.org
BASESCAN_API_KEY=
DATABASE_URL=
PRIVATE_KEY=
SCANNER_ADDRESS=
REGISTRY_ADDRESS=
RECENT_SCAN_FEED_URL=
RECENT_SCAN_INGEST_TOKEN=
ONCHAIN_LOG_ENABLED=false
BOT_PUBLISH_TO_REGISTRY=false
```

Base gas is ETH. Collector budget aliases support `MAX_ETH_TOTAL`, `TARGET_ETH_PER_SCAN`, and `ETH_EUR_PRICE_FALLBACK`.

## Contract

Compile:

```bash
npm ci
npm run compile
```

Deploy RugBusterScanner to Base:

```bash
npm run deploy:scanner:base
```

Verify on Basescan:

```bash
npx hardhat verify --network base <SCANNER_ADDRESS>
```

Production deployment:

```txt
SCANNER_ADDRESS=0x5F30276B3A5079E088Ec3072884286de5a868355
DEPLOY_TX=0x42cf163c4a443e6b34543861849ba2df49e87b93fc8bb69363d24528201f712d
```

## Railway Worker

`railway.json` starts the Base collector:

```txt
python chains/base/base_collector_v1.py
```

The worker initializes `base_scans` automatically when `DATABASE_URL` is set.

## API

Local API:

```bash
python api/server.py
```

Endpoints:

- `GET /health`
- `GET /score?address=0x...`
- `POST /api/scan`
- `GET /api/recent-scans?chain=base&limit=25`

## Landing Page

GitHub Pages serves `docs/index.html`. The page includes:

- dark RugBuster security-tool visual style
- â€œLive on Base mainnetâ€ badge
- live scan counter hook for `base_scans`
- deployed contract section
- CIA Engine five-module explanation
- scan endpoint and live Base feed links

Do not hardcode placeholder scan totals. The landing page reads the live scan count from the Base API.

