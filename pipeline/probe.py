"""Temporary: Maine layout + code frequencies; Florida 2022 archive + registration links."""
import re, io, requests, collections
import pandas as pd
H = {"User-Agent": "Mozilla/5.0 (EV-Model research; github.com/MoveBeyondFPTP/EV-Model)"}
def text(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
r = requests.get("https://www.maine.gov/sos/elections-voting/absenteelayout", headers=H, timeout=60)
t = text(r.text); i = t.find("RES MUNICIPALITY"); print("LAYOUT:", t[max(0, i-200):i+5000])
for name, u in {"2026": "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/11-3-26%20AB%20Voter%20File%20as%20of%2010-27-26.txt",
                "2022": "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/Absentee%20Voter%20File11822_0.txt"}.items():
    r = requests.get(u, headers=H, timeout=120)
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8", "replace")), sep="|", dtype=str, keep_default_na=False, on_bad_lines="skip")
    print(f"\n==== ME {name}: {len(df)} rows; columns {list(df.columns)}")
    for c in ["P", "Ballot Type", "Req Type", "Issued Type", "Rec Type", "Status", "DUP", "CH", "REJ", "DES"]:
        if c in df.columns: print(c, dict(collections.Counter(df[c]).most_common(15)))
    rd = pd.to_datetime(df.get("Rec Date", pd.Series(dtype=str)), format="%m/%d/%Y", errors="coerce")
    print("Rec Date range", rd.min(), rd.max(), "n with date", rd.notna().sum())
    print("by Rec Type x Status:", df[rd.notna()].groupby(["Rec Type", "Status"]).size().sort_values(ascending=False).head(15).to_dict())
    print("unique voter ids", df["Voter Record #"].nunique())
# Maine registration (E&R) files
r = requests.get("https://www.maine.gov/sos/elections-voting/voter-data", headers=H, timeout=60)
print("\nME voter-data links:", [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"E%26R|enroll|registration|\.xlsx|\.pdf", l, re.I)][:40])
r = requests.get("https://www.maine.gov/sos/elections-voting/voter-data/voter-registration-and-enrollment", headers=H, timeout=60)
print("\nME enrollment page", r.status_code, [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"xlsx|pdf|E%26R|enroll", l, re.I)][:60])
# Florida 2022 archive PDF
import pdfplumber
r = requests.get("https://dos.fl.gov/media/706191/2022-ge-rptstatuscountsarchive-ev-vbm.pdf", headers=H, timeout=120)
print("\nFL 2022 PDF", r.status_code, len(r.content))
with pdfplumber.open(io.BytesIO(r.content)) as pdf:
    print("pages", len(pdf.pages))
    for pg in pdf.pages[:3]:
        print("---- page"); print((pg.extract_text() or "")[:2500])
r = requests.get("https://dos.fl.gov/elections/data-statistics/voter-registration-statistics/", headers=H, timeout=60)
print("\nFL reg links:", [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"regist|book|xlsx|pdf", l, re.I)][:40])
