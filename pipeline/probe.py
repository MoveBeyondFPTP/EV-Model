"""Temporary: debug the Maine reader with full tracebacks and timings."""
import sys, time, traceback, io
sys.path.insert(0, "pipeline")
import pandas as pd
from sources import maine
er = "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/E%26R%203.7.26%20ACTIVE%20After%20Inactivation%20Process.xlsx"
t = time.time()
try:
    c = maine.get(er); print("got xlsx", len(c), round(time.time() - t, 1), "s")
    try:
        raw = pd.read_excel(io.BytesIO(c), header=None, dtype=str); print("read_excel ok", raw.shape); print(raw.head(3).to_string())
    except Exception:
        traceback.print_exc()
    print("registration:", maine.registration(c))
    m = maine.county_map(c); print("county map size", len(m), list(m.items())[:5])
except Exception:
    traceback.print_exc()
import json
cfg = json.load(open("pipeline/states/me.json"))["early_vote"]
for y in (2026, 2022):
    t = time.time()
    try:
        df, url = maine.load(cfg, y); print(y, len(df), round(time.time() - t, 1), "s"); print(df.head().to_string()); print(df["county"].value_counts().head(20).to_dict())
    except Exception:
        traceback.print_exc()
