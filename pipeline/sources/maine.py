"""Maine absentee voter files (ballot-level, with party and return dates).

Source: Maine Secretary of State, https://www.maine.gov/sos/elections-voting/voter-data
In Maine all early voting is absentee: "VP" returns are ballots voted in person at the
town clerk's office; everything else (mail, drop box, delivered) counts as mail here.
The 2022 and 2026 files use different column names; both are handled.
"""
from __future__ import annotations

import io
import re
import sys

import pandas as pd
import requests

H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
COUNTIES = {"AND": "Androscoggin", "ARO": "Aroostook", "CUM": "Cumberland", "FRA": "Franklin", "HAN": "Hancock",
            "KEN": "Kennebec", "KNO": "Knox", "LIN": "Lincoln", "OXF": "Oxford", "PEN": "Penobscot",
            "PIS": "Piscataquis", "SAG": "Sagadahoc", "SOM": "Somerset", "WAL": "Waldo", "WAS": "Washington",
            "YOR": "York"}
# column name -> candidates (2026 layout first, then 2022)
COLS = {"muni": ["RES MUNICIPALITY", "MUNICIPALITY"], "voter": ["Voter Record #", "VOTER ID"], "party": ["P"],
        "rec_type": ["Rec Type", "RECTYPE"], "rec_date": ["Rec Date", "RECDATE"], "status": ["Status", "ACC OR REJ"]}
ACCEPTED = {"ACT", "ACU", "ACH", "ACC"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url: str) -> bytes:
    r = requests.get(url, headers=H, timeout=600)
    r.raise_for_status()
    return r.content


def resolve_url(spec) -> str:
    """A file spec is either a URL or {"page": ..., "pattern": ...} to find today's file name on a page."""
    if isinstance(spec, str):
        return spec
    html = get(spec["page"]).decode("utf-8", "replace")
    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    hits = [l for l in links if re.search(spec["pattern"], requests.utils.unquote(l), re.I)]
    if not hits:
        raise RuntimeError(f"No link matching {spec['pattern']!r} on {spec['page']}")
    url = hits[0]
    return url if url.startswith("http") else "https://www.maine.gov" + url


def read_table(content: bytes) -> pd.DataFrame:
    """Registration/enrollment files come as .xlsx or delimited text; find the header row with party columns."""
    try:
        raw = pd.read_excel(io.BytesIO(content), header=None, dtype=str)
    except Exception:
        text = content.decode("utf-8", "replace")
        first = next(l for l in text.splitlines() if l.strip())
        sep = "|" if "|" in first else "\t" if "\t" in first else ","
        raw = pd.read_csv(io.StringIO(text), sep=sep, header=None, dtype=str, keep_default_na=False, on_bad_lines="skip")
    for i in range(min(20, len(raw))):
        row = [str(x).strip().upper() for x in raw.iloc[i].tolist()]
        if {"D", "R", "U"} <= set(row) and any("MUNICIPALITY" in x for x in row):
            df = raw.iloc[i + 1:].copy()
            df.columns = row
            return df
    raise ValueError("Couldn't find a header row with D/R/U columns")


def registration(content: bytes) -> dict:
    df = read_table(content)
    num = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
    df = df[df["MUNICIPALITY"].astype(str).str.strip().ne("") & df["MUNICIPALITY"].notna()]
    out = {"DEM": int(num("D").sum()), "REP": int(num("R").sum()), "UNA": int(num("U").sum()),
           "OTH": int(sum(num(c).sum() for c in df.columns if c in ("G", "L", "O", "W")))}
    return out


def county_map(content: bytes) -> dict:
    df = read_table(content)
    m = {}
    for county, muni in zip(df.get("COUNTY", []), df["MUNICIPALITY"]):
        if isinstance(muni, str) and isinstance(county, str) and county.strip().upper() in COUNTIES:
            m[muni.strip().upper()] = COUNTIES[county.strip().upper()]
    return m


def load(cfg: dict, year: int) -> tuple[pd.DataFrame, str]:
    files = cfg["files"]
    url = resolve_url(files[str(year)])
    log(f"Downloading {url}")
    text = get(url).decode("utf-8", "replace")
    df = pd.read_csv(io.StringIO(text), sep="|", dtype=str, keep_default_na=False, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    col = {k: next((c for c in v if c in df.columns), None) for k, v in COLS.items()}
    missing = [k for k, v in col.items() if v is None]
    if missing:
        raise ValueError(f"Maine file missing {missing}; columns were {list(df.columns)}")
    st = df[col["status"]].str.strip().str.upper()
    df = df[st.isin(ACCEPTED)]
    # County from the enrollment file's municipality -> county mapping.
    cmap = county_map(get(resolve_url(cfg["county_map"])))
    muni = df[col["muni"]].str.strip().str.upper()
    party = df[col["party"]].str.strip().str.upper().map({"D": "DEM", "R": "REP", "U": "UNA"}).fillna("OTH")
    rtype = df[col["rec_type"]].str.strip().str.upper()
    dates = pd.to_datetime(df[col["rec_date"]].str.strip().str[:10], format="%m/%d/%Y", errors="coerce")
    out = pd.DataFrame({
        "voter": df[col["voter"]].str.strip().values,
        "county": muni.map(cmap).fillna("Other / unorganized").values,
        "party": pd.Categorical(party, categories=["DEM", "REP", "UNA", "OTH"]),
        "method": pd.Categorical(rtype.map(lambda t: "in_person" if t == "VP" else "mail"), categories=["mail", "in_person"]),
        "age_b": pd.Categorical(["Unknown"] * len(df), categories=["18-25", "26-40", "41-65", "66+", "Unknown"]),
        "race_b": pd.Categorical(["Other/Unknown"] * len(df), categories=["White", "Black", "Other/Unknown"]),
        "rtn": dates.values,
    })
    log(f"  accepted: {len(out):,}; unmapped municipalities: {(out['county'] == 'Other / unorganized').sum():,}")
    return out, url
