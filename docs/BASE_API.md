# RugBuster Base API

Base API endpoints:

- `GET /health`
- `GET /score?address=0x...`
- `POST /api/scan`
- `GET /api/recent-scans?chain=base&limit=25`

The recent scan feed reads persisted rows from `base_scans`. Do not publish placeholder scan totals; show counts only after the collector has written real records.

## Current Production Values

- Railway URL: pending
- Scanner contract: pending
- Basescan verification: pending

## Example Recent Scans Request

```bash
curl "$RUGBUSTER_BASE_API/api/recent-scans?chain=base&limit=25"
```

## Example Scan Request

```bash
curl -X POST "$RUGBUSTER_BASE_API/api/scan" \
  -H "Content-Type: application/json" \
  -d '{"address":"0x4200000000000000000000000000000000000006"}'
```
