"""Temporary: Dallas EV spreadsheets (2026 + 2022), Bexar export, Fulton 2022 archive search."""
import re, io, requests
import pandas as pd
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
def links(u, pat):
    r = requests.get(u, headers=H, timeout=(15, 60))
    return r, [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(pat, l, re.I)]
for y, u in {"2026": "https://www.dallascountyvotes.org/election-results/historical/november-3-2026-general-and-joint-election/",
             "2022": "https://www.dallascountyvotes.org/election-results/historical/november-8-2022-general-and-joint-election/"}.items():
    r, ls = links(u, r"\.(xlsx?|csv|pdf)")
    print(f"\n== Dallas {y} docs:"); [print("  ", l) for l in ls[:20]]
    for l in ls:
        if re.search(r"early.?vot.*(total|location)|EV.?Totals|Totals.?by.?Location", l, re.I) and re.search(r"\.xlsx?$", l, re.I):
            c = requests.get(l, headers=H, timeout=(15, 120)).content
            try:
                x = pd.read_excel(io.BytesIO(c), header=None)
                print(f"  -> {l}\n  shape {x.shape}"); print(x.head(12).to_string()[:3500]); print(x.tail(4).to_string()[:1500])
            except Exception as e:
                print("  xls read failed", e)
            break
r, ls = links("https://earlyvotecountsdual.bexar.org/", r"export|\.csv|\.xls|javascript|__doPostBack")
print("\n== Bexar export links:", ls[:10])
print(re.findall(r'<form[^>]*>', r.text)[:3], re.findall(r'name="(__[A-Z]+)"', r.text)[:6])
for u in ["https://www.fultoncountyga.gov/Inside-Fulton-County/Fulton-County-Departments/Registration-and-Elections/Election-Results",
          "https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/registration-and-elections/election-reports"]:
    try:
        r, ls = links(u, r"2022|Nov.*8|advance|AV-Daily")
        print(f"\n== Fulton {u} -> {r.status_code}"); [print("  ", l) for l in ls[:25]]
    except Exception as e:
        print("Fulton err", e)
