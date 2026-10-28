"""Florida early vote and vote-by-mail totals (county x party), from the Division of Elections.

Florida publishes only running totals, not ballot-level files with dates, so each run
saves a dated snapshot and compares it with the 2022 general election's final totals
(from the Division's archived PDF report). Same-day comparisons with 2022 aren't
possible, so Florida gets no early-vote turnout adjustment in the projection.

Sources:
  https://countyfilesvbm-ev.floridados.gov/VoteByMailEarlyVotingReports/PublicStats
  https://dos.fl.gov/elections/data-statistics/elections-data/absentee-and-early-voting/
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
STATS_PAGE = "https://countyfilesvbm-ev.floridados.gov/VoteByMailEarlyVotingReports/PublicStats"
FILE = "https://electionfiles.floridados.gov/countyballotreportfiles/Stats_{n}_{kind}.txt"
KINDS = {"VbmVoted": "mail", "EarlyVoted": "in_person"}
PARTY_COLS = {"TotalDem": "DEM", "TotalRep": "REP", "TotalNpa": "UNA", "TotalOth": "OTH"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url):
    """GET with a connect/read timeout and two retries, so one slow site can't stall the whole update."""
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=(20, 120))
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            log(f"  retry {attempt + 1} for {url}: {e!r}")
    raise last


def num(s):
    s = str(s).replace(",", "").strip()
    return int(float(s)) if s else 0


def current(election_date: str) -> dict:
    """Today's totals: {"compiled": iso, "counties": {county: {method: {party: n}}}}."""
    page = get(STATS_PAGE).text
    ids = sorted(set(re.findall(r"Stats_(\d+)_", page)))
    if not ids:
        raise RuntimeError("No Florida stats files linked on the public stats page")
    out, compiled = {}, None
    for n in ids:
        for kind, method in KINDS.items():
            text = get(FILE.format(n=n, kind=kind)).content.decode("utf-8", "replace")
            lines = [l.split("\t") for l in text.splitlines() if l.strip()]
            head = [h.strip() for h in lines[0]]
            for row in lines[1:]:
                rec = dict(zip(head, [c.strip() for c in row]))
                ed = rec.get("ElectionDate", "")
                if ed and datetime.strptime(ed, "%m/%d/%Y").date().isoformat() != election_date:
                    break  # a different election's file
                county = rec["CountyName"]
                if county == "State Totals":
                    continue
                out.setdefault(county, {}).setdefault(method, {})
                for col, p in PARTY_COLS.items():
                    out[county][method][p] = num(rec.get(col, 0))
                c = rec.get("CompileDate")
                if c:
                    try:
                        dt = datetime.strptime(" ".join(c.split()), "%m/%d/%Y %I:%M%p")
                        compiled = max(compiled, dt) if compiled else dt
                    except ValueError:
                        pass
    if not out:
        raise RuntimeError("Florida stats files had no rows for this election")
    return {"compiled": compiled.isoformat() if compiled else None, "counties": out}


def final_2022(pdf_url: str) -> dict:
    """Parse the archived 2022 general election status-count PDF into county x method x party."""
    import pdfplumber
    content = get(pdf_url).content
    out, county = {}, None
    rx = re.compile(r"^(Voted Vote-by-Mail|Voted Early)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                line = line.strip()
                m = re.match(r"^(.+?)\s+Republican\s+Democrat\s+Other\s+Affiliation\s+TOTAL$", line)
                if m:
                    county = m.group(1).strip()
                    continue
                m = rx.match(line)
                if m and county and county != "STATE TOTAL":
                    method = "mail" if "Mail" in m.group(1) else "in_person"
                    rep, dem, oth, npa = (num(m.group(i)) for i in range(2, 6))
                    out.setdefault(county, {})[method] = {"REP": rep, "DEM": dem, "OTH": oth, "UNA": npa}
    if len(out) < 60:
        raise RuntimeError(f"Parsed only {len(out)} Florida counties from the 2022 PDF")
    return out


def build(cfg: dict, out_dir: Path, election_date: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    base_path = out_dir / "baseline_2022_final.json"
    if not base_path.exists():
        log(f"Parsing 2022 final totals from {cfg['baseline_pdf']}")
        base = final_2022(cfg["baseline_pdf"])
        base_path.write_text(json.dumps({"label": "2022 general, final", "counties": base,
                                         "source_url": cfg["baseline_pdf"]}, separators=(",", ":")))
    snap_path = out_dir / "snapshots.json"
    snaps = json.loads(snap_path.read_text()) if snap_path.exists() else {"snapshots": []}
    cur = current(election_date)
    ed = date.fromisoformat(election_date)
    compiled = cur["compiled"] or datetime.now(timezone.utc).isoformat()
    day = datetime.fromisoformat(compiled).date()
    totals = {m: {p: sum(c.get(m, {}).get(p, 0) for c in cur["counties"].values()) for p in PARTY_COLS.values()}
              for m in KINDS.values()}
    snap = {"date": day.isoformat(), "compiled": compiled, "days_out": (ed - day).days, "totals": totals}
    snaps["snapshots"] = [s for s in snaps["snapshots"] if s["date"] != snap["date"]] + [snap]
    snaps["snapshots"].sort(key=lambda s: s["date"])
    snaps["latest_counties"] = cur["counties"]
    snaps["election_date"] = election_date
    snaps["source_url"] = STATS_PAGE
    snap_path.write_text(json.dumps(snaps, separators=(",", ":")))
    log(f"  Florida snapshot {snap['date']}: mail {sum(totals['mail'].values()):,}, early {sum(totals['in_person'].values()):,}")
    return snaps
