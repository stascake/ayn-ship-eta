# AYN ship date estimator

Static page that estimates when an AYN Thor / Odin 3 order ships, based on the history of the
[AYN shipment dashboard](https://www.ayntec.com/pages/shipment-dashboard). Unofficial.

- `index.html` — the whole site; reads `data.json`.
- `archive/` — saved copies of the dashboard (Wayback Machine + daily copies). The live page drops old batches, so history lives here.
- `build_data.py` — merges `archive/` into `data.json`.
- `fetch.py` — downloads the live dashboard into `archive/` (only when it changed).
- `.github/workflows/update.yml` — runs fetch + build daily and deploys to GitHub Pages.

Local preview: `./run.sh` (http://127.0.0.1:8912).
