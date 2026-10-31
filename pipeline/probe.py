"""Temporary: results by vote method (NC, GA) for count-order benchmarks."""
import pathlib, requests
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
log = []
def get(name, url):
    try:
        r = requests.get(url, headers=H, timeout=(20, 300))
        if len(r.content) < 45_000_000: (OUT / name).write_bytes(r.content)
        log.append(f"{r.status_code} {len(r.content):>9} {name} {url}"); return r
    except Exception as e:
        log.append(f"ERR {name} {url} {e!r}")
get("nc_2022.zip", "https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/2022_11_08/results_pct_20221108.zip")
get("nc_2024.zip", "https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/2024_11_05/results_pct_20241105.zip")
for eid in ("115465",):
    r = get(f"ga_clarity_{eid}_ver.txt", f"https://results.enr.clarityelections.com/GA/{eid}/current_ver.txt")
    if r is not None and r.ok and r.text.strip().isdigit():
        v = r.text.strip()
        get(f"ga_clarity_{eid}_summary.json", f"https://results.enr.clarityelections.com/GA/{eid}/{v}/json/en/summary.json")
        get(f"ga_clarity_{eid}_detailxml.zip", f"https://results.enr.clarityelections.com/GA/{eid}/{v}/reports/detailxml.zip")
for n, u in [("ga_ev_2024.json", "https://results.sos.ga.gov/cdn/results/Georgia/export-2024NovGen.json"),
             ("ga_ev_index.html", "https://results.sos.ga.gov/results/public/Georgia")]:
    get(n, u)
(OUT / "_log.txt").write_text("\n".join(log)); print("\n".join(log))
