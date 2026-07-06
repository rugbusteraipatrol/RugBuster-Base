# Base Mainnet Runbook

1. Set `PRIVATE_KEY`, `BASE_RPC_URL`, and `BASESCAN_API_KEY`.
2. Compile with `npm run compile`.
3. Deploy with `npm run deploy:scanner:base`.
4. Verify with `npx hardhat verify --network base <SCANNER_ADDRESS>`.
5. Set Railway variables including `DATABASE_URL`, `BASE_RPC`, and `SCANNER_ADDRESS`.
6. Start the worker with `python chains/base/base_collector_v1.py`.
7. Update `docs/index.html` only after the contract and API are real.
