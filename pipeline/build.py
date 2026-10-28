"""Build early-vote summary JSON from a state's ballot-level absentee/early-vote file.

Each state is described by pipeline/states/<state>.json (election dates, which
years are baselines, the races to project, past results). For each election
this downloads the statewide file, keeps accepted ballots (one per voter), and
writes compact daily aggregates indexed by *days before Election Day* so
different cycles line up.

Usage:
    python pipeline/build.py                 # refresh the current year, build missing past years
    python pipeline/build.py --force         # rebuild every year
    python pipeline/build.py --years 2020    # only these years
    python pipeline/build.py --source-dir X  # read zips from X instead of downloading
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
STATES_DIR = ROOT / "pipeline" / "states"
DATA_DIR = ROOT / "docs" / "data"
CACHE_DIR = ROOT / ".cache"

# Column name -> candidate names in the file (matched case-insensitively).
COLUMNS = {
    "county": ["county_desc", "county"],
    "ncid": ["ncid"],
    "reg_num": ["voter_reg_num"],
    "party": ["voter_party_code", "party_code", "voter_party"],
    "race": ["race", "race_code"],
    "age": ["age", "voter_age"],
    "req_type": ["ballot_req_type", "ballot_request_type"],
    "rtn_dt": ["ballot_rtn_dt", "ballot_return_date"],
    "status": ["ballot_rtn_status", "ballot_return_status"],
}
REQUIRED = ["county", "party", "req_type", "rtn_dt", "status"]

PARTIES = ["DEM", "REP", "UNA", "OTH"]
METHODS = ["mail", "in_person"]
AGES = ["18-25", "26-40", "41-65", "66+", "Unknown"]
RACES = ["White", "Black", "Other/Unknown"]

TIMEOUT = 900


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def load_state(code: str) -> dict | None:
    """Return the state's early-vote config (with a few top-level fields), or None if it has none."""
    top = json.loads((STATES_DIR / f"{code}.json").read_text())
    ev = top.get("early_vote")
    if not ev:
        return None
    cfg = dict(ev)
    cfg.update(state=top["state"], name=top["name"], current=top["current"], code=code)
    cfg["elections"] = {int(y): date.fromisoformat(d) for y, d in ev["elections"].items()}
    return cfg


def download(cfg: dict, year: int, source_dir: Path | None) -> Path:
    d = cfg["elections"][year]
    url = cfg["source_url_template"].format(d=d)
    name = url.rsplit("/", 1)[-1]
    if source_dir:
        path = source_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / name
    log(f"Downloading {url}")
    headers = {"User-Agent": "EV-Model (github.com/MoveBeyondFPTP/EV-Model)"}
    with requests.get(url, stream=True, timeout=TIMEOUT, headers=headers) as r:
        r.raise_for_status()
        tmp = path.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.replace(path)
    log(f"  {path.stat().st_size / 1e6:.1f} MB")
    return path


def resolve_columns(header: list[str]) -> dict[str, str]:
    lower = {h.strip().lower(): h for h in header}
    found = {}
    for key, candidates in COLUMNS.items():
        for c in candidates:
            if c in lower:
                found[key] = lower[c]
                break
    missing = [k for k in REQUIRED if k not in found]
    if missing:
        raise ValueError(f"Missing columns {missing}. Header was: {header}")
    return found


def bucket_party(s: pd.Series) -> pd.Series:
    s = s.str.strip().str.upper()
    return s.where(s.isin(["DEM", "REP", "UNA"]), "OTH")


def bucket_method(s: pd.Series) -> pd.Series:
    s = s.str.strip().str.upper()
    in_person = s.str.contains("ONE") | s.str.contains("STOP") | s.str.contains("EARLY")
    return in_person.map({True: "in_person", False: "mail"})


def bucket_age(s: pd.Series) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    out = pd.Series("Unknown", index=s.index)
    out[(n >= 18) & (n <= 25)] = "18-25"
    out[(n >= 26) & (n <= 40)] = "26-40"
    out[(n >= 41) & (n <= 65)] = "41-65"
    out[n >= 66] = "66+"
    return out


def bucket_race(s: pd.Series) -> pd.Series:
    s = s.str.strip().str.upper()
    out = pd.Series("Other/Unknown", index=s.index)
    out[s.isin(["W", "WHITE"])] = "White"
    out[s.isin(["B", "BLACK", "BLACK OR AFRICAN AMERICAN"])] = "Black"
    return out


def parse_dates(s: pd.Series) -> pd.Series:
    s = s.str.strip()
    dt = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    alt = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    return dt.fillna(alt)


def cat(s: pd.Series, values: list[str]) -> pd.Series:
    return pd.Categorical(s, categories=values)


def read_ballots(zip_path: Path) -> pd.DataFrame:
    """Read accepted ballots, bucketing each chunk as it arrives to keep memory low."""
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        member = max(members, key=lambda m: zf.getinfo(m).file_size)
        log(f"  reading {member} ({zf.getinfo(member).file_size / 1e6:.0f} MB unzipped)")
        with zf.open(member) as raw:
            first = raw.readline().decode("utf-8-sig", errors="replace")
        delim = csv.Sniffer().sniff(first, delimiters=",\t|").delimiter
        header = next(csv.reader([first], delimiter=delim))
        cols = resolve_columns(header)
        log(f"  columns: {cols}")

        frames = []
        with zf.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
            reader = pd.read_csv(
                text, sep=delim, usecols=list(cols.values()), dtype=str, chunksize=500_000,
                keep_default_na=False, quotechar='"', on_bad_lines="warn",
            )
            for chunk in reader:
                chunk = chunk.rename(columns={v: k for k, v in cols.items()})
                for k in COLUMNS:
                    if k not in chunk.columns:
                        chunk[k] = ""
                chunk = chunk[chunk["status"].str.strip().str.upper().str.startswith("ACCEPTED")]
                if chunk.empty:
                    continue
                ncid = chunk["ncid"].str.strip()
                fallback = chunk["county"].str.strip() + "|" + chunk["reg_num"].str.strip()
                frames.append(pd.DataFrame({
                    "voter": ncid.where(ncid != "", fallback).values,
                    "county": chunk["county"].str.strip().str.title().values,
                    "party": cat(bucket_party(chunk["party"]), PARTIES),
                    "method": cat(bucket_method(chunk["req_type"]), METHODS),
                    "age_b": cat(bucket_age(chunk["age"]), AGES),
                    "race_b": cat(bucket_race(chunk["race"]), RACES),
                    "rtn": parse_dates(chunk["rtn_dt"]).values,
                }))
    if not frames:
        return pd.DataFrame(columns=["voter", "county", "party", "method", "age_b", "race_b", "rtn"])
    df = pd.concat(frames, ignore_index=True)
    df["county"] = df["county"].astype("category")
    return df


def summarize(df: pd.DataFrame, cfg: dict, year: int) -> dict:
    election = pd.Timestamp(cfg["elections"][year])
    df = df.dropna(subset=["rtn"])
    # Dates in the future are data-entry errors; drop them so they can't move "as of".
    today = pd.Timestamp(datetime.now(timezone.utc).date())
    future = df["rtn"] > today
    if future.any():
        log(f"  dropping {int(future.sum())} rows with return dates after today")
        df = df[~future]

    # One ballot per voter: keep the earliest accepted return.
    has_id = df["voter"].str.strip("|") != ""
    with_id = df[has_id].sort_values("rtn").drop_duplicates("voter", keep="first")
    df = pd.concat([with_id, df[~has_id]], ignore_index=True)

    late = int((df["rtn"] > election).sum())
    # Window: 90 days before Election Day. Anything earlier (or a mistyped date years in the past)
    # is folded into day 90 so one bad record can't blow up the file size.
    MAX_WINDOW = 90
    bad = int(((election - df["rtn"]).dt.days > MAX_WINDOW).sum())
    if bad:
        log(f"  {bad} ballots dated more than {MAX_WINDOW} days out; counted on day {MAX_WINDOW}")
    df = df.assign(days_out=(election - df["rtn"]).dt.days.clip(lower=0, upper=MAX_WINDOW))

    max_days = min(max(int(df["days_out"].max()) if len(df) else 0, 60), MAX_WINDOW)
    days = list(range(max_days, -1, -1))  # descending: far out -> Election Day

    def series(group_col: str | None, values: list[str]):
        if group_col is None:
            counts = df.groupby("days_out").size()
            return [int(counts.get(d, 0)) for d in days]
        counts = df.groupby([group_col, "days_out"], observed=True).size()
        return {v: [int(counts.get((v, d), 0)) for d in days] for v in values}

    counties = {}
    cc = df.groupby(["county", "party", "days_out"], observed=True).size()
    for county in sorted(df["county"].astype(str).unique()):
        if not county:
            continue
        counties[county] = {p: [int(cc.get((county, p, d), 0)) for d in days] for p in PARTIES}

    as_of = df["rtn"].max()
    as_of_clipped = min(as_of, election) if pd.notna(as_of) else None
    return {
        "state": cfg["state"],
        "year": year,
        "election_date": cfg["elections"][year].isoformat(),
        "as_of": as_of_clipped.date().isoformat() if as_of_clipped is not None else None,
        "as_of_days_out": int((election - as_of_clipped).days) if as_of_clipped is not None else None,
        "total": int(len(df)),
        "returned_after_election_day": late,
        "source_url": None,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days_out": days,
        "daily": {
            "total": series(None, []),
            "method": series("method", METHODS),
            "party": series("party", PARTIES),
            "age": series("age_b", AGES),
            "race": series("race_b", RACES),
        },
        "counties": counties,
    }


def build(cfg: dict, year: int, source_dir: Path | None) -> dict:
    log(f"== {cfg['state']} {year}")
    if cfg.get("type") == "maine":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sources import maine
        df, url = maine.load(cfg, year)
        path = None
    else:
        path = download(cfg, year, source_dir)
        df = read_ballots(path)
        url = cfg["source_url_template"].format(d=cfg["elections"][year])
    log(f"  accepted rows: {len(df):,}")
    summary = summarize(df, cfg, year)
    summary["source_url"] = url
    log(f"  unique accepted ballots: {summary['total']:,}; as of {summary['as_of']}")
    if summary["total"] == 0:
        raise RuntimeError(f"No accepted ballots found for {year}; refusing to overwrite data")
    if source_dir is None and path is not None:
        path.unlink(missing_ok=True)  # free runner disk before the next year
    return summary


def write_json(obj: dict, path: Path):
    text = json.dumps(obj, separators=(",", ":"))
    if len(text) > 5_000_000:  # summaries should be well under 1 MB; refuse to write something that would break the push
        raise RuntimeError(f"{path.name} would be {len(text) / 1e6:.0f} MB; refusing to write")
    path.write_text(text)
    log(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e3:.0f} KB)")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="nc")
    ap.add_argument("--force", action="store_true", help="rebuild past years too")
    ap.add_argument("--years", type=int, nargs="*", help="only these years")
    ap.add_argument("--source-dir", type=Path, help="read zips from here instead of downloading")
    args = ap.parse_args()

    top = json.loads((STATES_DIR / f"{args.state}.json").read_text())
    if top.get("county_samples"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sources import counties
        counties.build(args.state, top["county_samples"], DATA_DIR / args.state)
    cfg = load_state(args.state)
    if cfg is None:
        log(f"{args.state}: no early-vote source configured; skipping")
        return
    current = cfg["current"]
    OUT_DIR = DATA_DIR / args.state
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cfg.get("type") == "florida":
        # Running totals only: save today's snapshot and compare with 2022's final totals.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sources import florida
        florida.build(cfg, OUT_DIR, cfg["elections"][current].isoformat())
        write_json({"state": cfg["state"], "name": cfg["name"], "current": current, "kind": "snapshot",
                    "baselines": [], "calibration": None, "source_page": cfg.get("source_page"),
                    "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                   OUT_DIR / "manifest.json")
        return
    years = args.years or list(cfg["elections"])
    failures = []
    for year in years:
        out = OUT_DIR / f"{year}.json"
        if year != current and out.exists() and not args.force:
            log(f"== {year}: already built, skipping")
            continue
        try:
            write_json(build(cfg, year, args.source_dir), out)
        except Exception as e:  # keep going so one bad file doesn't block the others
            log(f"!! {year} failed: {e!r}")
            failures.append(year)

    have = lambda y: (OUT_DIR / f"{y}.json").exists()
    cal = cfg.get("calibration")
    manifest = {
        "state": cfg["state"],
        "name": cfg["name"],
        "current": current,
        "baselines": [y for y in cfg["baselines"] if have(y)],
        "calibration": cal if cal and have(cal["from"]["year"]) and have(cal["to"]["year"]) else None,
        "source_page": cfg.get("source_page"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(manifest, OUT_DIR / "manifest.json")
    if failures:
        log(f"Failed years: {failures}")
        sys.exit(1)


if __name__ == "__main__":
    main()
