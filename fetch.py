"""Download the live AYN shipment dashboard into archive/ (used by the daily GitHub Action).

Saves archive/snap_<UTC timestamp>.html.gz only when the batch list differs from the newest
snapshot, and writes archive/checked_at.txt after every successful check. Then run build_data.py.
Exits 0 on fetch failure (the shop rate-limits with 429): the site just keeps the old data.
"""
import datetime
import glob
import gzip
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from build_data import parse, read

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://www.ayntec.com/pages/shipment-dashboard?view=raw"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.0 Safari/605.1.15")


def fetch():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError:
        # python.org builds on macOS often ship without root certs; curl uses the system store
        out = subprocess.run(["curl", "-sfL", "--max-time", "30", "-A", UA, URL],
                             capture_output=True, check=True)
        return out.stdout.decode("utf-8", "replace")


def main():
    page = None
    for attempt in range(4):
        try:
            page = fetch()
            if parse(page):
                break
            print("page fetched but no batches found", file=sys.stderr)
        except Exception as e:
            print(f"attempt {attempt + 1}: {e}", file=sys.stderr)
        page = None
        time.sleep(90)
    if page is None:
        print("giving up; keeping old data", file=sys.stderr)
        return 0

    now = datetime.datetime.now(datetime.timezone.utc)
    snaps = sorted(glob.glob(os.path.join(HERE, "archive", "snap_*.html*")))
    if snaps and parse(read(snaps[-1])) == parse(page):
        print("dashboard unchanged")
    else:
        path = os.path.join(HERE, "archive", f"snap_{now:%Y%m%d%H%M%S}.html.gz")
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(page)
        print(f"saved {os.path.basename(path)}")
    with open(os.path.join(HERE, "archive", "checked_at.txt"), "w") as f:
        f.write(now.strftime("%Y-%m-%dT%H:%MZ") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
