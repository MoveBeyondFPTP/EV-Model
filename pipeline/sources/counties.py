"""County-level early-vote samples for states whose statewide data can't be fetched.

Each county source returns cumulative in-person early votes by days before Election Day,
for 2026 and for the comparison year, so the page can show pace against the same point
in that year. These are a sample of one large county, not the state, and they don't feed
the projection.

Currently: Dallas County, Texas (Dallas County Elections Department, daily "Early Voting
Turnout By Date & Location" spreadsheets; 2022's are archived on the same site).
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url):
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


def find_link(page: str, pattern: str) -> str:
    html = get(page).text
    for l in re.findall(r'href=["\']([^"\']+)["\']', html):
        if re.search(pattern, requests.utils.unquote(l), re.I):
            return l.replace("&amp;", "&")
    raise RuntimeError(f"No link matching {pattern!r} on {page}")


def read_sheet(content: bytes) -> pd.DataFrame:
    for engine in ("openpyxl", "xlrd"):
        try:
            return pd.read_excel(io.BytesIO(content), header=None, engine=engine)
        except Exception:
            pass
    tables = pd.read_html(io.BytesIO(content), header=None)  # some ".xls" files are HTML tables
    return max(tables, key=len)


def as_date(v):
    if isinstance(v, (datetime, pd.Timestamp)):
        return pd.Timestamp(v).date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%b %d", "%d-%b"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def daily_totals(df: pd.DataFrame, year: int) -> dict:
    """Find the header row of dates; use the 'Total' row if there is one, else sum the location rows."""
    for i in range(min(len(df), 30)):
        cols = {}
        for j, v in enumerate(df.iloc[i].tolist()):
            d = as_date(v)
            if d:
                if d.year == 1900:  # month-day only
                    d = d.replace(year=year)
                cols[j] = d
        if len(cols) >= 2:
            body = df.iloc[i + 1:]
            names = body.iloc[:, 0].astype(str).str.strip()
            total_rows = body[names.str.contains("total", case=False, na=False)]
            if len(total_rows):
                row = total_rows.iloc[0]
                return {cols[j].isoformat(): int(pd.to_numeric(row.iloc[j], errors="coerce") or 0) for j in cols}
            loc = body[names.ne("") & names.ne("nan")]
            return {cols[j].isoformat(): int(pd.to_numeric(loc.iloc[:, j], errors="coerce").fillna(0).sum()) for j in cols}
    raise ValueError("Couldn't find a header row of dates")


def cumulative_by_days_out(daily: dict, election: date) -> dict:
    out, total = {}, 0
    for d in sorted(daily):
        total += daily[d]
        out[str((election - date.fromisoformat(d)).days)] = total
    return out


def dallas(cfg: dict) -> dict:
    url26 = find_link(cfg["page_2026"], r"Early-Voting-Turnout-By-Date-Location.*\.xlsx?$")
    url22 = cfg["file_2022"]
    log(f"  Dallas 2026: {url26}")
    d26 = daily_totals(read_sheet(get(url26).content), 2026)
    e26, e22 = date(2026, 11, 3), date(2022, 11, 8)
    then = {}
    try:  # the 2022 archive sits behind a bot challenge; use it only if it comes through
        then = cumulative_by_days_out(daily_totals(read_sheet(get(url22).content), 2022), e22)
    except Exception as e:
        log(f"  Dallas 2022 unavailable: {e!r}")
    return {"county": "Dallas County", "kind": "In-person early votes", "lean_2024": cfg.get("lean_2024"),
            "now": cumulative_by_days_out({k: v for k, v in d26.items() if v > 0}, e26),
            "daily": {k: v for k, v in d26.items() if v > 0},
            "then": then, "then_year": 2022,
            "source_page": cfg["page_2026"], "source_2026": url26, "source_2022": url22}


SOURCES = {"dallas": dallas}


def build(code: str, cfgs: list, out_dir: Path):
    results = []
    for c in cfgs:
        try:
            results.append(SOURCES[c["source"]](c))
            log(f"  {code} {c['source']}: ok")
        except Exception as e:
            log(f"!! {code} {c['source']} failed: {e!r}")
    if results:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "county_ev.json").write_text(json.dumps({
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "counties": results}, indent=1))
    return results
