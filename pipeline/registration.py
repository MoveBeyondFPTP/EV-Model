"""Statewide voter registration by party, from a state's registration-stats files.

Writes docs/data/registration.json: {year: {"DEM": n, "REP": n, "UNA": n, "OTH": n, "label": ...}}.
Snapshots that already exist are kept unless --force.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}

PARTY_COLS = ["party_cd", "party_code", "party"]
COUNT_COLS = ["total_voters", "voters", "count"]


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def tally(content: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        member = max((m for m in zf.namelist() if not m.endswith("/")), key=lambda m: zf.getinfo(m).file_size)
        with zf.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
            first = text.readline()
            delim = csv.Sniffer().sniff(first, delimiters=",\t|").delimiter
            header = [h.strip().lower() for h in next(csv.reader([first], delimiter=delim))]
            pi = next((header.index(c) for c in PARTY_COLS if c in header), None)
            ci = next((header.index(c) for c in COUNT_COLS if c in header), None)
            if pi is None or ci is None:
                raise ValueError(f"Can't find party/count columns in {header}")
            out = {"DEM": 0, "REP": 0, "UNA": 0, "OTH": 0}
            for row in csv.reader(text, delimiter=delim):
                if len(row) <= max(pi, ci):
                    continue
                p = row[pi].strip().upper()
                try:
                    n = int(float(row[ci] or 0))
                except ValueError:
                    continue
                out[p if p in ("DEM", "REP", "UNA") else "OTH"] += n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="nc")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "pipeline" / "states" / f"{args.state}.json").read_text())
    reg = (cfg.get("early_vote") or {}).get("registration")
    OUT = ROOT / "docs" / "data" / args.state / "registration.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not reg:
        log("No registration config; skipping")
        return
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    for year, snap in reg["snapshots"].items():
        if year in data and not args.force:
            continue
        url = snap.get("url") or reg["url_template"].format(path=snap["path"])
        try:
            log(f"Downloading {url}")
            r = requests.get(url, headers=H, timeout=600)
            r.raise_for_status()
            if snap.get("format") == "maine":
                sys.path.insert(0, str(ROOT / "pipeline"))
                from sources import maine
                counts = maine.registration(r.content)
            else:
                counts = tally(r.content)
            total = sum(counts.values())
            log(f"  {year}: {counts} total {total:,}")
            if total < 1000:
                raise ValueError("implausibly small total")
            data[year] = {**counts, "label": snap["label"]}
        except Exception as e:
            log(f"!! registration {year} failed: {e!r}")
    OUT.write_text(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
