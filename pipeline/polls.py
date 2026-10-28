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
API = "https://api.votehub.com/polls"
H = {"User-Agent": "EV-Model (github.com/MoveBeyondFPTP/EV-Model)"}

WINDOW_DAYS = 30        # primary window
FALLBACK_DAYS = 60      # used when fewer than MIN_POLLS fall in the primary window
MIN_POLLS = 3
HALF_LIFE = 14          # days
POP_RANK = {"lv": 0, "rv": 1, "a": 2}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def matcher(side: dict):
    """Return a function giving the summed share of every answer matching this side
    (several Republicans in one ranked-choice race add together)."""
    inc = [m.lower() for m in side.get("match", [])]
    exc = [m.lower() for m in side.get("exclude", [])]
    def f(answers):
        total, hit = 0.0, False
        for a in answers or []:
            c = str(a.get("choice", "")).lower()
            if any(m in c for m in inc) and not any(x in c for x in exc):
                try:
                    total += float(a["pct"]); hit = True
                except (TypeError, ValueError, KeyError):
                    pass
        return total if hit else None
    return f


def average(polls, get_d, get_r, today: date, windows=(WINDOW_DAYS, FALLBACK_DAYS), min_polls=MIN_POLLS):
    rows = []
    for p in polls:
        try:
            end = date.fromisoformat(p["end_date"])
        except Exception:
            continue
        if end > today:
            continue
        d, r = get_d(p.get("answers")), get_r(p.get("answers"))
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


def fetch_type(poll_type: str, since: date):
    r = requests.get(API, params={"poll_type": poll_type, "from_date": since.isoformat()}, headers=H, timeout=120)
    r.raise_for_status()
    return [p for p in r.json() if p.get("poll_type") == poll_type]


def manual(mp: dict):
    """Turn hand-entered polls (e.g. ballot measures VoteHub doesn't cover) into VoteHub-shaped records."""
    return [{**p, "url": p.get("url") or mp.get("source_url"),
             "answers": [{"choice": "__dem__", "pct": p["dem"]}, {"choice": "__rep__", "pct": p["rep"]}]}
            for p in mp["polls"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", nargs="*", help="state codes (default: all configured)")
    args = ap.parse_args()
    states_dir = ROOT / "pipeline" / "states"
    codes = args.states or sorted(p.stem for p in states_dir.glob("*.json"))
    nat = json.loads((ROOT / "pipeline" / "national.json").read_text())
    today = datetime.now(timezone.utc).date()
    since = date.fromordinal(today.toordinal() - 125)
    meta = {
        "source": "VoteHub", "source_url": "https://votehub.com/polls/", "license": "CC BY 4.0",
        "method": f"One poll per pollster from the last {WINDOW_DAYS} days ({FALLBACK_DAYS} if fewer than {MIN_POLLS}), "
                  f"likely voters preferred, weighted by recency (half-life {HALF_LIFE} days) and sample size; "
                  "partisan or internal polls count half. Margins are two-party.",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    cache = {}

    def polls_of(pt):
        if pt not in cache:
            try:
                cache[pt] = fetch_type(pt, since)
                log(f"fetched {len(cache[pt])} {pt} polls")
            except Exception as e:
                log(f"!! fetching {pt} failed: {e!r}")
                cache[pt] = None
        return cache[pt]

    # National generic ballot (sparser in VoteHub, so look back further for at least 5 polls).
    g = polls_of("generic-ballot")
    nat_out = ROOT / "docs" / "data" / "national.json"
    if g is not None:
        subj = nat["generic_ballot"]["subject"]
        gen = average([p for p in g if p.get("subject") == subj],
                      matcher({"match": ["dem"]}), matcher({"match": ["rep"]}), today, windows=(30, 45, 60), min_polls=5)
        nat_out.write_text(json.dumps({**meta, "generic": gen, "prior": nat["prior"]}, indent=1))
        log(f"generic ballot: {gen['avg']} from {gen['n']} polls")

    for code in codes:
        cfg = json.loads((states_dir / f"{code}.json").read_text())
        out_path = ROOT / "docs" / "data" / code / "polls.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prev = json.loads(out_path.read_text()) if out_path.exists() else {"races": {}}
        out = {**meta, "races": {}}
        for race in cfg["races"]:
            rid = race["id"]
            try:
                if race.get("manual_polls"):
                    mp = race["manual_polls"]
                    res = average(manual(mp), matcher({"match": ["__dem__"]}), matcher({"match": ["__rep__"]}), today,
                                  windows=(30, 60, 120), min_polls=2)
                    res.update(source=mp["source"], source_url=mp["source_url"], manual=True)
                else:
                    ps = polls_of(race["poll_type"])
                    if ps is None:
                        out["races"][rid] = prev["races"].get(rid)  # keep the last good result if the API is down
                        continue
                    ps = [p for p in ps if p.get("subject") == cfg["polls"]["subject"]]
                    res = average(ps, matcher(race["dem"]), matcher(race["rep"]), today)
                    fb = race.get("fallback_polls")
                    if res["n"] == 0 and fb:  # nothing recent in VoteHub: use hand-entered polls, looking back up to 120 days
                        res = average(manual(fb), matcher({"match": ["__dem__"]}), matcher({"match": ["__rep__"]}), today,
                                      windows=(30, 60, 120), min_polls=1)
                        res.update(source=fb["source"], source_url=fb["source_url"], manual=True)
                out["races"][rid] = res
                log(f"{code} {rid}: {res['avg']} from {res['n']} polls")
            except Exception as e:
                log(f"!! {code} {rid} failed: {e!r}")
                out["races"][rid] = prev["races"].get(rid)
        out_path.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
