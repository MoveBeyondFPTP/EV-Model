"""Temporary: fetch raw sources for the local-measure model into probe_out/."""
import re, pathlib, requests
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
log = []
def get(name, url, method="get", **kw):
    try:
        r = requests.request(method, url, headers=H, timeout=(20, 180), **kw)
        (OUT / name).write_bytes(r.content)
        log.append(f"{r.status_code} {len(r.content):>9} {name} {url}")
    except Exception as e:
        log.append(f"ERR {name} {url} {e!r}")
S = "https://hicscdata.hawaii.gov/resource/"
for ds in ("rajm-32md", "riiu-7d4b"):
    get(f"hicsc_{ds}_sample.json", f"{S}{ds}.json?$limit=3")
    for q in ("ranked", "rcv", "charter", "question 5"):
        get(f"hicsc_{ds}_{q.replace(' ','_')}.json", f"{S}{ds}.json", params={"$q": q, "$limit": 5000})
    get(f"hicsc_{ds}_2026.json", f"{S}{ds}.json", params={"$where": "date >= '2026-01-01T00:00:00'", "$limit": 50000})
get("netfile_get.json", "https://netfile.com/Connect2/api/public/list/filing?AID=IRV&Application=Campaign&format=json")
get("netfile_export_2026.zip", "https://netfile.com/Connect2/api/public/campaign/export/cal201/transaction/year/2026?aid=IRV")
get("netfile_export_2026b.zip", "https://netfile.com/Connect2/api/public/campaign/export/cal201/transaction/year/2026?AID=IRV")
get("longmont_fcpa.html", "https://longmontcolorado.gov/city-clerk/election-information/fair-campaign-practices-act/")
get("longmont_past.html", "https://longmontcolorado.gov/city-clerk/election-information/past-election-results/")
get("longmont_measures.html", "https://longmontcolorado.gov/city-clerk/election-information/november-3-2026-election-ballot-measures/")
get("boco_returns.html", "https://election.boco.solutions/CR_WebReporting/BallotReturns?electionName=2026G")
get("boco_returns_2024.html", "https://election.boco.solutions/CR_WebReporting/BallotReturns?electionName=2024G")
get("boco_returns_2022.html", "https://election.boco.solutions/CR_WebReporting/BallotReturns?electionName=2022G")
(OUT / "_log.txt").write_text("\n".join(log))
print("\n".join(log))
