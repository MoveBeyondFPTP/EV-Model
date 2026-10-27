"""Temporary: inspect data sources from GitHub's runners."""
import json, requests, collections
H = {"User-Agent": "EV-Model (github.com/MoveBeyondFPTP/EV-Model)"}
def get(u, **kw):
    r = requests.get(u, headers=H, timeout=120, **kw); print("GET", u, r.status_code, len(r.content)); return r
for ep in ["poll-types", "subjects"]:
    r = get(f"https://api.votehub.com/{ep}")
    print(r.text[:4000])
r = get("https://api.votehub.com/polls", params={"from_date": "2026-08-01"})
polls = r.json()
print("n polls since Aug:", len(polls))
print("keys:", list(polls[0].keys()) if polls else None)
c = collections.Counter((p.get("poll_type"), p.get("subject")) for p in polls)
for k, v in c.most_common(80): print(" ", v, k)
seats = collections.Counter((p.get("poll_type"), p.get("seat_name")) for p in polls)
for k, v in seats.most_common(80): print(" seat", v, k)
for p in polls:
    txt = json.dumps(p)
    if "Cooper" in txt and "Whatley" in txt:
        print("NC SAMPLE:", txt[:1500]); break
for p in polls:
    if p.get("poll_type") == "generic-ballot":
        print("GENERIC SAMPLE:", json.dumps(p)[:1200]); break
pops = collections.Counter(p.get("population") for p in polls); print("populations", pops)
for d in ["2020_11_03/voter_stats_20201103.zip", "2022_11_08/voter_stats_20221108.zip",
          "2024_11_05/voter_stats_20241105.zip", "2026_11_03/voter_stats_20261103.zip",
          "2026_03_03/voter_stats_20260303.zip"]:
    u = "https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/" + d
    r = requests.head(u, headers=H, timeout=60); print("HEAD", u, r.status_code, r.headers.get("Content-Length"), r.headers.get("Last-Modified"))
r = get("https://s3.amazonaws.com/dl.ncsbe.gov?list-type=2&prefix=ENRS/2026_11_03/")
print(r.text[:3000])
r = get("https://s3.amazonaws.com/dl.ncsbe.gov?list-type=2&prefix=data/")
print(r.text[:3000])
