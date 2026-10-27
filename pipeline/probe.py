"""Temporary: Maine 2022 codes, Maine enrollment files, Florida 2022 archive + registration."""
import re, io, requests, collections
import pandas as pd
H = {"User-Agent": "Mozilla/5.0 (EV-Model research; github.com/MoveBeyondFPTP/EV-Model)"}
u = "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/Absentee%20Voter%20File11822_0.txt"
r = requests.get(u, headers=H, timeout=120)
df = pd.read_csv(io.StringIO(r.content.decode("utf-8", "replace")), sep="|", dtype=str, keep_default_na=False, on_bad_lines="skip")
print(df.head(5).to_string())
for c in ["REQTYPE", "ISSTYPE", "RECTYPE", "ACC OR REJ", "REJRSN"]:
    print(c, dict(collections.Counter(df[c]).most_common(15)))
print("RECDATE samples", df["RECDATE"].head(20).tolist())
for name, u in {"voter-data": "https://www.maine.gov/sos/elections-voting/voter-data",
                "reg-enroll": "https://www.maine.gov/sos/elections-voting/voter-data/registration-and-enrollment-statistics"}.items():
    r = requests.get(u, headers=H, timeout=60)
    ls = [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"E%26R|enroll|regist|\.xlsx|\.pdf", l, re.I) and "bmv" not in l and "archives" not in l]
    print("\nME", name, r.status_code, ls[:60])
import pdfplumber
r = requests.get("https://dos.fl.gov/media/706191/2022-ge-rptstatuscountsarchive-ev-vbm.pdf", headers=H, timeout=120)
print("\nFL 2022 PDF", r.status_code, len(r.content))
with pdfplumber.open(io.BytesIO(r.content)) as pdf:
    print("pages", len(pdf.pages))
    for k in (0, 1, len(pdf.pages) - 1):
        print(f"---- page {k}"); print((pdf.pages[k].extract_text() or "")[:2500])
r = requests.get("https://dos.fl.gov/elections/data-statistics/voter-registration-statistics/", headers=H, timeout=60)
print("\nFL reg links:", [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"regist|book|xlsx|pdf", l, re.I)][:50])
