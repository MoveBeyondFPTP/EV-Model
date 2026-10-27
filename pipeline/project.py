"""Preliminary projections for every configured state and race.

For each race:
  A. Environment: a past result (by default the state's 2024 presidential vote),
     moved by the change in the national generic ballot since then.
  B. Polls: blend A with the race's own polling average; weight on polls is
     n / (n + 2), capped at 80%.
  C. Early vote (states with party-registration early-vote data only): a small
     turnout adjustment. How much more Democratic the early electorate is than
     the registered pool, compared with the same point in the last midterm.
     Counted at 25%, capped at +/-2 points.

Writes docs/data/<state>/projection.json and docs/data/index.json.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
STATES = ROOT / "pipeline" / "states"

ASSUME = {"dem": 0.92, "rep": 0.92, "una": 0.50, "oth": 0.45}
C_WEIGHT, C_WEIGHTS, C_CAP, POLL_W_MAX = 0.25, (0.0, 0.25, 0.5), 2.0, 0.8


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ---------- early-vote helpers (party-registration states) ----------
def party_counts(data, day):
    out = {}
    for p, arr in data["daily"]["party"].items():
        out[p] = sum(v for v, d in zip(arr, data["days_out"]) if d >= day)
    return out


def implied(c, a=ASSUME):
    D = c["DEM"] * a["dem"] + c["REP"] * (1 - a["rep"]) + c["UNA"] * a["una"] + c["OTH"] * a["oth"]
    R = c["DEM"] * (1 - a["dem"]) + c["REP"] * a["rep"] + c["UNA"] * (1 - a["una"]) + c["OTH"] * (1 - a["oth"])
    return (D - R) / (D + R) * 100 if D + R else None


def excess(data, reg, day):
    if not data or not reg:
        return None
    e, r = implied(party_counts(data, day)), implied(reg)
    return None if e is None or r is None else e - r


def turnout_signal(code: str, ev_cfg: dict):
    d = DATA / code
    man = load(d / "manifest.json")
    if not man or not man.get("baselines"):
        return None
    cur = load(d / f"{man['current']}.json")
    reg = load(d / "registration.json") or {}
    if not cur:
        return None
    day = cur["as_of_days_out"]
    by = man["baselines"][0]
    base = load(d / f"{by}.json")
    now, then = excess(cur, reg.get(str(man["current"])), day), excess(base, reg.get(str(by)), day)
    if now is None or then is None:
        return None
    sig = {"value": round(now - then, 2), "now": round(now, 2), "then": round(then, 2), "year": by, "day": day,
           "as_of": cur["as_of"]}
    # Backtest on the calibration pair: did the same signal point the right way?
    cal = man.get("calibration")
    if cal and cal["from"].get("national_margin") is not None:
        a, b = load(d / f"{cal['to']['year']}.json"), load(d / f"{cal['from']['year']}.json")
        ea, eb = excess(a, reg.get(str(cal["to"]["year"])), day), excess(b, reg.get(str(cal["from"]["year"])), day)
        if ea is not None and eb is not None and b["days_out"][0] >= day:
            s = ea - eb
            state_move = cal["to"]["margin"] - cal["from"]["margin"]
            nat_move = cal["to"]["national_margin"] - cal["from"]["national_margin"]
            adj = clamp(C_WEIGHT * s, -C_CAP, C_CAP)
            rel = state_move - nat_move
            sig["backtest"] = {"from": cal["from"]["year"], "to": cal["to"]["year"], "label": cal["to"]["label"],
                               "signal": round(s, 2), "adjustment": round(adj, 2), "state_move": round(state_move, 2),
                               "national_move": round(nat_move, 2), "relative": round(rel, 2),
                               "right_direction": bool(abs(adj) > 0.05 and (adj > 0) == (rel > 0))}
    return sig


# ---------- projection ----------
def rating(center, lo, hi, dem_short, rep_short, measure=False):
    leader = dem_short if center > 0 else rep_short
    if lo < 0 < hi:
        return "Toss-up" if abs(center) < 0.5 else f"Toss-up, slight edge {leader}"
    a = abs(center)
    if measure:
        return f"{'Leans' if a < 7 else 'Likely'} {leader}"
    return f"{'Tilt' if a < 3 else 'Lean' if a < 7 else 'Likely' if a < 12 else 'Solid'} {leader}"


def project_race(race, cfg, generic, polls, signal):
    env_cfg = race.get("environment") or cfg["environment"]
    A = None
    if generic is not None:
        factor = env_cfg.get("swing_factor", 1.0)
        swing = (generic - env_cfg["national_margin"]) * factor
        A = {"label": env_cfg["label"], "base": env_cfg["margin"], "national_then": env_cfg["national_margin"],
             "generic": generic, "swing_factor": factor, "swing": round(swing, 2),
             "margin": round(env_cfg["margin"] + swing, 2), "note": env_cfg.get("swing_note")}
    P = polls if polls and polls.get("avg") is not None else None
    if not A and not P:
        return None
    wp = (min(POLL_W_MAX, P["n"] / (P["n"] + 2)) if A else 1.0) if P else 0.0
    start = wp * P["avg"] + (1 - wp) * A["margin"] if (P and A) else (P["avg"] if P else A["margin"])
    use_c = signal is not None and race.get("type") == "candidate" and race["dem"].get("party") == "D"
    adj_at = (lambda k: clamp(k * signal["value"], -C_CAP, C_CAP)) if use_c else (lambda k: 0.0)
    adj = adj_at(C_WEIGHT)
    starts = [start] + ([A["margin"]] if A else []) + ([P["avg"]] if P else [])
    allv = [s + adj_at(k) for s in starts for k in (C_WEIGHTS if use_c else (0.0,))]
    center = start + adj
    lo, hi = min(allv), max(allv)
    return {
        "center": round(center, 2), "lo": round(lo, 2), "hi": round(hi, 2),
        "rating": rating(center, lo, hi, race["dem"]["short"], race["rep"]["short"], race.get("type") == "measure"),
        "environment": A,
        "polls": {"avg": P["avg"], "n": P["n"], "window_days": P["window_days"]} if P else None,
        "poll_weight": round(wp, 3), "start": round(start, 2),
        "early_vote": {"adjustment": round(adj, 2), "weight": C_WEIGHT, "cap": C_CAP} if use_c else None,
    }


def main():
    nat = load(DATA / "national.json")
    generic = nat["generic"]["avg"] if nat and nat.get("generic") else None
    index = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "generic": nat["generic"] if nat else None, "prior": nat.get("prior") if nat else None, "states": []}
    for path in sorted(STATES.glob("*.json")):
        code = path.stem
        cfg = load(path)
        pol = load(DATA / code / "polls.json") or {"races": {}}
        signal = turnout_signal(code, cfg["early_vote"]) if cfg.get("early_vote") else None
        races = []
        for race in cfg["races"]:
            p = project_race(race, cfg, generic, pol["races"].get(race["id"]), signal)
            races.append({k: race.get(k) for k in ("id", "office", "type", "note", "dem", "rep", "comparison_result")}
                         | {"projection": p})
            if p:
                log(f"{code} {race['id']}: {p['center']:+.1f} ({p['rating']})")
        out = {"state": cfg["state"], "code": code, "name": cfg["name"], "election_date": cfg["election_date"],
               "has_early_vote": bool(cfg.get("early_vote")) and (DATA / code / "manifest.json").exists(),
               "turnout_signal": signal, "races": races,
               "ev_notes": (cfg.get("early_vote") or {}).get("notes", []),
               "generated_at": index["generated_at"], "assumptions": ASSUME,
               "constants": {"c_weight": C_WEIGHT, "c_cap": C_CAP, "poll_weight_max": POLL_W_MAX}}
        (DATA / code).mkdir(parents=True, exist_ok=True)
        (DATA / code / "projection.json").write_text(json.dumps(out, indent=1))
        index["states"].append({
            "code": code, "name": cfg["name"], "has_early_vote": out["has_early_vote"],
            "early_vote_as_of": signal["as_of"] if signal else None,
            "races": [{"id": r["id"], "office": r["office"], "type": r["type"],
                       "dem": r["dem"]["short"], "rep": r["rep"]["short"],
                       "dem_party": r["dem"].get("party"), "rep_party": r["rep"].get("party"),
                       **({k: r["projection"][k] for k in ("center", "lo", "hi", "rating")} if r["projection"] else {}),
                       "n_polls": (r["projection"]["polls"] or {}).get("n", 0) if r["projection"] else 0}
                      for r in races],
        })
    (DATA / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
