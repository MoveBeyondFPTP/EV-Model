"""Temporary: fetch Orange County results archive pages."""
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
r = get("oc_archives.html", "https://www.ocvote.gov/data/election-results-archives")
if r is not None and r.ok:
    links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
    cand = [l for l in links if re.search(r"2024|gen2024|nov2024|results", l, re.I)]
    (OUT / "oc_archive_links.txt").write_text("\n".join(links))
    for i, l in enumerate([l for l in cand if re.search(r"2024", l)][:12]):
        u = l if l.startswith("http") else "https://www.ocvote.gov" + l
        p = get(f"oc_2024_{i}.html", u)
        if p is not None and p.ok and "html" in p.headers.get("content-type", ""):
            sub = sorted(set(re.findall(r'href="([^"]+)"', p.text)))
            (OUT / f"oc_2024_{i}_links.txt").write_text("\n".join(sub))
            for j, s in enumerate([s for s in sub if re.search(r"\.(zip|xlsx?|csv|txt)$", s, re.I)][:15]):
                su = s if s.startswith("http") else requests.compat.urljoin(u, s)
                get(f"oc_2024_{i}_{j}_" + su.rsplit("/", 1)[-1][-60:], su)
(OUT / "_log.txt").write_text("\n".join(log)); print("\n".join(log))
