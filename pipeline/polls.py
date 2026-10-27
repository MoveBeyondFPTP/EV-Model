"""Polling averages from VoteHub (https://votehub.com/polls/, CC BY 4.0).

For each race in the state config, and for the national generic ballot, take
recent polls, keep one per pollster (its most recent, preferring likely-voter
samples), and average the two-party margin with weights for recency and sample
size. Partisan or internal polls count half.

Writes docs/data/polls.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "polls.json"
API = "https://api.votehub.com/polls"
H = {"User-Agent": "EV-Model (github.com/MoveBeyondFPTP/EV-Model)"}

WINDOW_DAYS = 30        # primary window
FALLBACK_DAYS = 60      # used when fewer than MIN_POLLS fall in the primary window
MIN_POLLS = 3
HALF_LIFE = 14          # days
POP_RANK = {"lv": 0, "rv": 1, "a": 2}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def last(name: str) -> str:
    return name.strip().split()[-1].lower()


def pick(answers, key_d, key_r):
    d = r = None
    for a in answers or []:
        c = str(a.get("choice", "")).lower()
        if d is None and key_d(c):
            d = float(a["pct"])
        elif r is None and key_r(c):
            r = float(a["pct"])
    return d, r


def average(polls, key_d, key_r, today: date, windows=(WINDOW_DAYS, FALLBACK_DAYS), min_polls=MIN_POLLS):
    rows = []
    for p in polls:
        try:
            end = date.fromisoformat(p["end_date"])
        except Exception:
            continue
        if end > today:
            continue
        d, r = pick(p.get("answers"), key_d, key_r)
        if d is None or r is None or d + r <= 0:
            continue
        rows.append({
            "pollster": p.get("pollster") or "Unknown",
            "end_date": end.isoformat(),
            "age": (today - end).days,
            "population": (p.get("population") or "").lower(),
            "sample_size": p.get("sample_size"),
            "dem": d, "rep": r,
            "margin": round((d - r) / (d + r) * 100, 2),
            "partisan": bool(p.get("partisan") or p.get("internal")),
            "url": p.get("url"),
        })
    for window in windows:
        recent = [r for r in rows if r["age"] <= window]
        best = {}
        for r in sorted(recent, key=lambda r: (r["age"], POP_RANK.get(r["population"], 3))):
            best.setdefault(r["pollster"].lower(), r)  # one per pollster: newest, then LV first
        chosen = list(best.values())
        if len(chosen) >= min_polls or window == windows[-1]:
            break
    if not chosen:
        return {"avg": None, "n": 0, "window_days": None, "polls": []}
    tw = tm = 0.0
    for r in chosen:
        n = r["sample_size"] or 600
        w = 0.5 ** (r["age"] / HALF_LIFE) * min(math.sqrt(n / 600), 1.5) * (0.5 if r["partisan"] else 1.0)
        r["weight"] = round(w, 3)
        tw += w
        tm += w * r["margin"]
    chosen.sort(key=lambda r: r["end_date"], reverse=True)
    return {"avg": round(tm / tw, 2), "n": len(chosen), "window_days": window, "polls": chosen}


def fetch(poll_type: str, subject: str, since: date):
    r = requests.get(API, params={"poll_type": poll_type, "from_date": since.isoformat()}, headers=H, timeout=120)
    r.raise_for_status()
    return [p for p in r.json() if p.get("subject") == subject and p.get("poll_type") == poll_type]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="nc")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "pipeline" / "states" / f"{args.state}.json").read_text())
    nat = json.loads((ROOT / "pipeline" / "national.json").read_text())
    today = datetime.now(timezone.utc).date()
    since = date.fromordinal(today.toordinal() - FALLBACK_DAYS - 5)
    out = {
        "source": "VoteHub",
        "source_url": "https://votehub.com/polls/",
        "license": "CC BY 4.0",
        "method": f"One poll per pollster from the last {WINDOW_DAYS} days ({FALLBACK_DAYS} if fewer than {MIN_POLLS}), "
                  f"likely voters preferred, weighted by recency (half-life {HALF_LIFE} days) and sample size; "
                  "partisan or internal polls count half. Margins are two-party, D minus R.",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generic": None,
        "races": {},
    }
    try:
        g = fetch("generic-ballot", nat["generic_ballot"]["subject"], since)
        # National polls are sparser in VoteHub, so look back further for at least 5.
        out["generic"] = average(g, lambda c: c.startswith("dem"), lambda c: c.startswith("rep"), today,
                                 windows=(30, 45, 60), min_polls=5)
        log(f"generic ballot: {out['generic']['avg']} from {out['generic']['n']} polls")
    except Exception as e:
        log(f"!! generic ballot failed: {e!r}")
    subject = cfg["polls"]["subject"]
    for race in cfg.get("races", []):
        try:
            ps = fetch(race["poll_type"], subject, since)
            dl, rl = last(race["dem"]), last(race["rep"])
            res = average(ps, lambda c: dl in c, lambda c: rl in c, today)
            out["races"][race["office"]] = res
            log(f"{race['office']}: {res['avg']} from {res['n']} polls")
        except Exception as e:
            log(f"!! {race['office']} polls failed: {e!r}")
    if OUT.exists() and out["generic"] is None and not out["races"]:
        log("Nothing fetched; keeping previous polls.json")
        return
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
