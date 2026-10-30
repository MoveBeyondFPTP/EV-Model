"""Temporary: fetch raw sources for the local-measure model into probe_out/."""
import re, pathlib, requests, urllib.parse
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
log = []
def get(name, url, method="get", **kw):
    try:
        r = requests.request(method, url, headers=H, timeout=(20, 120), **kw)
        (OUT / name).write_bytes(r.content)
        log.append(f"{r.status_code} {len(r.content):>9} {name} {url}")
    except Exception as e:
        log.append(f"ERR {name} {url} {e!r}")
def wiki(title):
    get("wiki_" + re.sub(r"\W+", "_", title) + ".json",
        "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&formatversion=2&redirects=1&page=" + urllib.parse.quote(title))
for y in range(2010, 2025, 2):
    g = "General" if y == 2024 else "general"
    get(f"hi_{y}_media.txt", f"https://files.hawaii.gov/elections/files/results/{y}/{g}/media.txt")
    get(f"hi_{y}_cch.pdf", f"https://files.hawaii.gov/elections/files/results/{y}/{g}/cch.pdf")
get("hicsc_catalog.json", "https://api.us.socrata.com/api/catalog/v1?domains=hicscdata.hawaii.gov&limit=100")
get("netfile_list.json", "https://netfile.com/Connect2/api/public/list/filing", method="post",
    json={"AID": "IRV", "Application": "Campaign", "CurrentPageIndex": 0, "PageSize": 100})
get("netfile_agencies.json", "https://netfile.com/Connect2/api/public/campaign/list/agency?format=json")
get("longmont_clerk.html", "https://longmontcolorado.gov/city-clerk/election-information/")
get("longmont_cf.html", "https://longmontcolorado.gov/city-clerk/election-information/campaign-finance/")
get("oc_datacentral.html", "https://www.ocvote.gov/datacentral/")
get("oc_results.html", "https://www.ocvote.gov/results")
get("oc_trends.html", "https://www.ocvote.gov/data/voting-trends")
for t in ["Ojai, California", "Eureka, California", "Albany, California", "Richmond, California", "Redondo Beach, California",
          "Boulder, Colorado", "Broomfield, Colorado", "Fort Collins, Colorado", "Evanston, Illinois", "Oak Park, Illinois",
          "Skokie, Illinois", "Westbrook, Maine", "Portland, Maine", "Easthampton, Massachusetts", "East Lansing, Michigan",
          "Kalamazoo, Michigan", "Royal Oak, Michigan", "Ann Arbor, Michigan", "Minnetonka, Minnesota", "Bloomington, Minnesota",
          "Burlington, Vermont", "Portland, Oregon", "Seattle", "Austin, Texas", "2024 Oregon elections",
          "2024 United States presidential election in Washington (state)", "2024 United States presidential election in Oregon",
          "2024 United States presidential election in the District of Columbia", "2024 United States presidential election in New York",
          "Clark County, Washington", "San Juan County, Washington", "Honolulu County, Hawaii", "Longmont, Colorado"]:
    wiki(t)
(OUT / "_log.txt").write_text("\n".join(log))
print("\n".join(log))
