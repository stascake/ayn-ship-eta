"""Download the live AYN shipment dashboard into archive/ (used by the daily GitHub Action).

AYN rate-limits datacenter IPs (GitHub runners always get 429), so after two direct attempts
this asks the Wayback Machine to take a fresh copy and downloads that instead.

Saves archive/snap_<UTC timestamp>.html.gz only when the batch list differs from the newest
snapshot, and writes archive/checked_at.txt (when the data was seen) after every successful check.
Exits 0 when everything fails: the site just keeps the old data. Then run build_data.py.
"""
import datetime
import glob
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from build_data import parse, read

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "https://www.ayntec.com/pages/shipment-dashboard"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.0 Safari/605.1.15")


def get(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError:
        # python.org builds on macOS often ship without root certs; curl uses the system store
        raw = subprocess.run(["curl", "-sfL", "--max-time", str(timeout), "-A", UA, url],
                             capture_output=True, check=True).stdout
    if raw[:2] == b"\x1f\x8b":  # Wayback id_ pages keep the original gzip encoding
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def direct():
    for attempt in range(2):
        try:
            page = get(PAGE + "?view=raw")
            if parse(page):
                return page, datetime.datetime.now(datetime.timezone.utc)
            print("direct: page has no batches", file=sys.stderr)
        except Exception as e:
            print(f"direct attempt {attempt + 1}: {e}", file=sys.stderr)
        time.sleep(30)
    return None


def wayback():
    try:  # the archive's servers aren't blocked; this takes ~1 minute and may fail when it's busy
        get("https://web.archive.org/save/" + PAGE, timeout=180)
    except Exception as e:
        print(f"wayback save: {e}", file=sys.stderr)
    rows = json.loads(get("https://web.archive.org/cdx/search/cdx?url=ayntec.com/pages/shipment-dashboard"
                          "&output=json&fl=timestamp,original&filter=statuscode:200&limit=-5", timeout=120))[1:]
    for ts, original in reversed(rows):  # newest first
        page = get(f"https://web.archive.org/web/{ts}id_/{original}", timeout=120)
        if parse(page):
            when = datetime.datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
            return page, when
    return None


def main():
    got = direct()
    if got is None:
        try:
            got = wayback()
        except Exception as e:
            print(f"wayback: {e}", file=sys.stderr)
    if got is None:
        print("giving up; keeping old data", file=sys.stderr)
        return 0
    page, when = got
    print(f"got dashboard as of {when:%Y-%m-%d %H:%M} UTC")

    snaps = sorted(glob.glob(os.path.join(HERE, "archive", "snap_*.html*")))
    if snaps and parse(read(snaps[-1])) == parse(page):
        print("dashboard unchanged")
    else:
        path = os.path.join(HERE, "archive", f"snap_{when:%Y%m%d%H%M%S}.html.gz")
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(page)
        print(f"saved {os.path.basename(path)}")
    with open(os.path.join(HERE, "archive", "checked_at.txt"), "w") as f:
        f.write(when.strftime("%Y-%m-%dT%H:%MZ") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
