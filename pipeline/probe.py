"""Temporary: Statewide Database precinct files for Orange County (c059), 2024 general and primary."""
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
for page in ["g24", "g24_geo_conv", "p24", "p24_geo_conv"]:
    u = f"https://statewidedatabase.org/d20/{page}.html"
    r = get(f"swdb_{page}.html", u)
    if r is None or not r.ok: continue
    links = sorted(set(re.findall(r"href=['\"]([^'\"]+)['\"]", r.text)))
    (OUT / f"swdb_{page}_links.txt").write_text("\n".join(links))
    for l in links:
        if re.search(r"c059", l, re.I) and re.search(r"\.(zip|csv|txt)$", l, re.I) and re.search(r"sov|city|srprec|rgprec|mprec", l, re.I):
            get("swdb_" + l.rsplit("/", 1)[-1], requests.compat.urljoin(u, l))
(OUT / "_log.txt").write_text("\n".join(log)); print("\n".join(log))
