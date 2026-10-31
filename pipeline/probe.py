"""Temporary: find precinct-level 2024 results for Irvine."""
import pathlib, requests, re
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
log = []
def get(name, url):
    try:
        r = requests.get(url, headers=H, timeout=(20, 300)); (OUT / name).write_bytes(r.content)
        log.append(f"{r.status_code} {len(r.content):>9} {name} {url}"); return r
    except Exception as e:
        log.append(f"ERR {name} {url} {e!r}")
for n, u in [("oc_gen2024_results.htm", "https://www.ocvote.gov/fileadmin/live/gen2024/results.htm"),
             ("oc_gen2024_dir.html", "https://www.ocvote.gov/fileadmin/live/gen2024/"),
             ("oc_gen2018_results.htm", "https://ocvote.gov/fileadmin/live/gen2018/results.htm"),
             ("swdb_g24.html", "https://statewidedatabase.org/d10/g24.html"),
             ("swdb_index.html", "https://statewidedatabase.org/election.html")]:
    r = get(n, u)
    if r is not None and r.ok and n.startswith("swdb_g24"):
        links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        (OUT / "swdb_g24_links.txt").write_text("\n".join(links))
        for l in links:
            if re.search(r"c059.*(sov|city|srprec|precinct)|city", l, re.I) and re.search(r"\.(zip|csv|dbf|txt)$", l, re.I):
                get("swdb_" + l.rsplit("/", 1)[-1], requests.compat.urljoin("https://statewidedatabase.org/d10/", l))
    if r is not None and r.ok and n.startswith("oc_gen2024"):
        links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        (OUT / (n + "_links.txt")).write_text("\n".join(links))
        for l in links:
            if re.search(r"\.(zip|xlsx?|csv|txt)$", l, re.I):
                get("oc24_" + l.rsplit("/", 1)[-1], requests.compat.urljoin(u, l))
(OUT / "_log.txt").write_text("\n".join(log)); print("\n".join(log))
