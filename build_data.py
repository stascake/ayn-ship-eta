"""Merge saved copies of the AYN shipment dashboard into data.json (no network).

The live page only shows recent batches and drops old ones, so archive/ holds
Wayback Machine snapshots (archive/snap_<timestamp>.html, some gzipped), copies saved by hand
and the daily copies fetch.py saves (snap_<timestamp>.html.gz). Every batch line ever seen is kept; when the same
(date, model) appears in several snapshots the newest snapshot wins.

Usage: python3 -I build_data.py
"""
import glob
import gzip
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = "https://www.ayntec.com/pages/shipment-dashboard"

DATE_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")
ROW_RE = re.compile(r"^AYN\s+(Thor|Odin\s*3)\s+(.+?)\s*[:：]\s*(\d+)\s*xx\s*-+\s*(\d+)\s*xx", re.I)


def read(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def parse(page):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", page))
    rows, date = [], None
    for line in (l.strip() for l in text.splitlines()):
        if not line:
            continue
        if line.startswith("Get updates") and rows:
            break
        m = DATE_RE.match(line)
        if m:
            y, mo, d = map(int, m.groups())
            date = f"{y:04d}-{mo:02d}-{d:02d}"
            continue
        m = ROW_RE.match(line)
        if m and date:
            family = "Odin3" if m.group(1).lower().startswith("odin") else "Thor"
            variant = m.group(2).replace("（", " (").replace("）", ")")
            variant = re.sub(r"\s+", " ", variant).strip()
            variant = re.sub(r"\b[a-z]", lambda c: c.group().upper(), variant)  # "Clear purple" typos
            rows.append((date, f"{family} {variant}", int(m.group(3)), int(m.group(4))))
    return rows


def main():
    merged, snaps = {}, []
    for path in sorted(glob.glob(os.path.join(HERE, "archive", "snap_*.html*"))):
        rows = parse(read(path))
        if not rows:
            continue
        snaps.append(os.path.basename(path)[5:13])
        for date, model, lo, hi in rows:
            merged[(date, model, lo)] = hi  # sorted by timestamp, so later snapshots overwrite
    # an edited range (same date+model, different start) — keep only the newest
    latest = {}
    for (date, model, lo), hi in merged.items():
        latest[(date, model)] = (lo, hi)
    batches = {}
    for (date, model), (lo, hi) in sorted(latest.items()):
        batches.setdefault(date, []).append({"model": model, "from": lo, "to": hi})
    checked = os.path.join(HERE, "archive", "checked_at.txt")
    data = {
        "source": SOURCE,
        # last time the live dashboard was checked (fetch.py), else the newest snapshot's date
        "checked_at": open(checked).read().strip() if os.path.exists(checked) else snaps[-1],
        "snapshots": snaps,
        "batches": [{"date": d, "items": items} for d, items in sorted(batches.items())],
    }
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(snaps)} snapshots with data -> {len(data['batches'])} batch dates, "
          f"{sum(len(b['items']) for b in data['batches'])} rows, "
          f"{data['batches'][0]['date']} .. {data['batches'][-1]['date']}")


if __name__ == "__main__":
    main()
