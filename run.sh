#!/bin/sh
# Serve the estimator locally. The page only reads data.json.
# Fresh data: python3 fetch.py && python3 -I build_data.py (GitHub Actions does this daily)
cd "$(dirname "$0")"
PORT=8912
lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 || (python3 -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 &)
sleep 0.5
open "http://127.0.0.1:$PORT/"
