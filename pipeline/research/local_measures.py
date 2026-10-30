"""Data-backed estimates for local ranked-choice-voting ballot measures.

Run by hand (not in the scheduled workflow): python pipeline/research/local_measures.py
It rewrites the "assessment" numbers of each local measure in pipeline/states/*.json.

Method
  1. Cross-section model: across 10 local RCV adoption votes (2016-2024) whose electorate's
     2024 presidential vote is published, regress Yes share on Harris's two-party share.
  2. Local anchor: the same electorate's own vote on the closest comparable question.
       Longmont  - Boulder and Broomfield RCV votes, moved to Longmont's partisanship with the
                   step-1 slope (both cities voted almost exactly like Longmont on Prop 131).
       Irvine    - Irvine's March 2024 Measure D (council expansion + districts).
       Honolulu  - Honolulu's past charter amendments on how city officials are elected.
  3. Estimate = average of 1 and 2. Uncertainty from the step-1 residual spread.
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATES = ROOT / "pipeline" / "states"

# (place, Harris 2024 two-party %, Yes %) - Yes from Ballotpedia / Wikipedia; partisanship from Wikipedia
# election tables, or Boulder County's precinct statement of votes for Boulder city.
CROSS = [("Albany, CA (2020)", 90.9, 73.0), ("Broomfield, CO (2021)", 64.7, 51.9),
         ("Redondo Beach, CA (Mar 2023)", 67.7, 76.7), ("Boulder, CO (2020)", 87.7, 78.1),
         ("Washington, DC (2024)", 93.3, 72.9), ("New York City (2019)", 69.4, 73.6),
         ("Multnomah County, OR (2022)", 82.2, 69.1), ("Benton County, OR (2016)", 70.5, 54.2),
         ("Clark County, WA (2022)", 53.6, 41.9), ("San Juan County, WA (2022)", 76.7, 45.6)]
# Honolulu charter amendments on electing city officials (Hawaii Office of Elections results files)
HNL_ELECTION = [("2016 Term limits for city offices", 36.7), ("2016 Nonpartisan reapportionment commission", 35.4),
                ("2016 Special election time extension", 55.5), ("2020 Term limits for prosecuting attorney", 83.2)]
HNL_ALL = {"n": 42, "mean": 64.0, "passed_pct": 83}

def fit(rows):
    n = len(rows); xs = [r[1] for r in rows]; ys = [r[2] for r in rows]
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sd = math.sqrt(sum(r * r for r in res) / (n - 2))
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return a, b, sd, r, res

A, B, SD, R, RES = fit(CROSS)
SD_EST = SD * math.sqrt(0.6)  # averaging two partly independent estimates trims the spread (~9 pts)
Z80 = 1.2816
phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))

def rate(p):
    if p >= 0.85: return "Likely Yes"
    if p >= 0.65: return "Leans Yes"
    if p > 0.55: return "Toss-up, slight edge Yes"
    if p >= 0.45: return "Toss-up"
    if p > 0.35: return "Toss-up, slight edge No"
    return "Leans No" if p > 0.15 else "Likely No"

def estimate(harris, anchor, anchor_label, anchor_detail, extra_sd=0.0):
    pred = A + B * harris
    est = (pred + anchor) / 2
    sd = math.hypot(SD_EST, extra_sd)
    p = phi((est - 50) / sd)
    return {"yes": round(est, 1), "yes_lo": round(est - Z80 * sd, 1), "yes_hi": round(est + Z80 * sd, 1),
            "p_pass": round(p, 2), "rating": rate(p),
            "model": {"harris_2p": harris, "cross_pred": round(pred, 1), "anchor": round(anchor, 1),
                      "anchor_label": anchor_label, "anchor_detail": anchor_detail,
                      "fit": {"n": len(CROSS), "slope": round(B, 2), "intercept": round(A, 1), "resid_sd": round(SD, 1), "r": round(R, 2)},
                      "sd": round(sd, 1), "cross": [{"label": c[0], "harris": c[1], "yes": c[2], "resid": round(e, 1)} for c, e in zip(CROSS, RES)]}}

# Longmont: Prop 131 (2024) Yes was 48.8% in Longmont's precincts, 48.1% in Boulder city's, 48.2% in Broomfield.
lm_h = 70.1
bould = 78.1 + B * (lm_h - 87.7)
broom = 51.9 + B * (lm_h - 64.7)
longmont = estimate(lm_h, (bould + broom) / 2, "Boulder and Broomfield RCV votes, adjusted to Longmont",
                    f"On 2024’s statewide Prop 131, Longmont (48.8% Yes), Boulder city (48.1%) and Broomfield (48.2%) voted almost identically. "
                    f"Their own city RCV votes were 78.1% and 51.9%; moved to Longmont’s partisanship that’s {bould:.1f}% and {broom:.1f}%.")
irvine = estimate(61.3, 59.8, "Irvine’s 2024 Measure D (council size and districts)",
                  "Irvine voters approved the last change to how the council is elected (March 2024 Measure D) with 59.8%.")
hnl_anchor = sum(v for _, v in HNL_ELECTION) / len(HNL_ELECTION)
honolulu = estimate(61.0, hnl_anchor, "Honolulu’s past charter amendments on electing officials",
                    "Four Honolulu charter amendments since 2010 changed how city officials are elected: "
                    + ", ".join(f"{l[5:].lower()} ({v}%)" for l, v in HNL_ELECTION)
                    + f", averaging {hnl_anchor:.1f}%. All {HNL_ALL['n']} Honolulu charter amendments since 2010 averaged {HNL_ALL['mean']}% and {HNL_ALL['passed_pct']}% passed.")
# 3D has no comparable data; it rides on 3C with an assumed 4-point drop-off and extra uncertainty.
d = dict(longmont); d3 = {**longmont, "model": {**longmont["model"]}}
est = longmont["yes"] - 4; sd = math.hypot(longmont["model"]["sd"], 4)
p = phi((est - 50) / sd)
d3.update(yes=round(est, 1), yes_lo=round(est - Z80 * sd, 1), yes_hi=round(est + Z80 * sd, 1), p_pass=round(p, 2), rating=rate(p))
d3["model"].update(sd=round(sd, 1), companion_of="Longmont Question 3C", dropoff=4)

OUT = {"ca": {"irvine-d": irvine}, "hi": {"honolulu-q5": honolulu}, "co": {"longmont-3c": longmont, "longmont-3d": d3}}
for code, races in OUT.items():
    p = STATES / f"{code}.json"; cfg = json.loads(p.read_text())
    for r in cfg["races"]:
        if r["id"] in races:
            r["assessment"].update(races[r["id"]])
            print(code, r["id"], races[r["id"]]["yes"], races[r["id"]]["yes_lo"], races[r["id"]]["yes_hi"], races[r["id"]]["p_pass"], races[r["id"]]["rating"],
                  "| cross", races[r["id"]]["model"]["cross_pred"], "anchor", races[r["id"]]["model"]["anchor"])
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
print(f"fit: yes = {A:.1f} + {B:.2f} x Harris2p, resid sd {SD:.1f}, r {R:.2f}")
