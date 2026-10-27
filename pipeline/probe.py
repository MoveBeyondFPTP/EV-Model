"""Temporary: Maine enrollment (registration by party) files."""
import re, io, requests
import pandas as pd
H = {"User-Agent": "Mozilla/5.0 (EV-Model research; github.com/MoveBeyondFPTP/EV-Model)"}
r = requests.get("https://www.maine.gov/sos/elections-voting/voter-data/previous-enrollment-data", headers=H, timeout=60)
ls = [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"\.(xlsx?|pdf|txt|csv)", l, re.I) and "bmv" not in l and "archives" not in l]
print("previous enrollment:", r.status_code); [print("  ", l) for l in ls[:80]]
u = "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/E%26R%203.7.26%20ACTIVE%20After%20Inactivation%20Process.xlsx"
r = requests.get(u, headers=H, timeout=60); print("\nE&R 2026", r.status_code, len(r.content))
x = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
for name, df in x.items():
    print("sheet", name, df.shape); print(df.head(12).to_string()); print(df.tail(5).to_string())
