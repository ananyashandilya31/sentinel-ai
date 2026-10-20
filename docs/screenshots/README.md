# Screenshots

Placeholder folder for the SentinelAI SOC console screenshots referenced in
the top-level README.

The images are **not committed** — generate them locally:

```bash
# 1. start the stack
docker compose up --build

# 2. seed demo data (all five attack scenarios)
python scripts/demo_seed.py

# 3. capture the console
npm i -D puppeteer          # one-off
node scripts/capture_screenshots.mjs
```

The capture script logs in, visits each tab and writes these files here:

| File | Screen |
|---|---|
| `01-dashboard.png` | SOC dashboard with live alert stream |
| `02-incidents.png` | Incident triage table |
| `03-ml-anomalies.png` | ML anomaly predictions |
| `04-threat-intel.png` | Threat intelligence view |
| `05-security-logs.png` | Security log explorer |
| `06-system-health.png` | System health panel |
| `07-incident-detail.png` | Incident detail drawer with AI investigation |
| `08-login.png` | Login screen |

Until they are captured, the README shows placeholders rather than broken
images.
