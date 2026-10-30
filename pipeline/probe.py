"""Temporary: fetch raw sources for the local-measure model into probe_out/."""
import json, re, pathlib, requests, urllib.parse
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
log = []
def get(name, url, **kw):
    try:
        r = requests.get(url, headers=H, timeout=(20, 120), **kw)
        (OUT / name).write_bytes(r.content)
        log.append(f"{r.status_code} {len(r.content):>9} {name} {url}")
        return r
    except Exception as e:
        log.append(f"ERR {name} {url} {e!r}")
def wiki(title):
    get("wiki_" + re.sub(r"\W+", "_", title) + ".html",
        "https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&formatversion=2&page=" + urllib.parse.quote(title))
for t in ["2024 Colorado Proposition 131", "Oregon Ballot Measure 117", "2024 Nevada Question 3",
          "2022 Nevada Question 3", "2024 Alaska Ballot Measure 2", "2020 Massachusetts Question 2",
          "2024 United States presidential election in Colorado", "2024 United States presidential election in Oregon",
          "2024 United States presidential election in Nevada", "2020 United States presidential election in Massachusetts",
          "2024 United States presidential election in Hawaii", "2024 United States presidential election in California",
          "Irvine, California", "Longmont, Colorado", "2024 Irvine elections", "Ranked-choice voting in the United States"]:
    wiki(t)
# Boulder County statements of votes (precinct level)
get("boulder_2024G_sov.pdf", "https://assets.bouldercounty.gov/wp-content/uploads/2024/11/2024G-Boulder-County-Official-Statement-of-Votes.pdf")
get("boulder_2024G_results.html", "https://electionresults.bouldercounty.gov/ElectionResults2024G/")
get("boulder_2023C_sov_summary.pdf", "https://assets.bouldercounty.gov/wp-content/uploads/2023/11/2023C-Boulder-County-Official-Summary-of-Votes.pdf")
get("boulder_2025C_results.html", "https://electionresults.bouldercounty.gov/ElectionResults2025C/")
get("boulder_2026G_results.html", "https://electionresults.bouldercounty.gov/ElectionResults2026G/")
get("boulder_elections_page.html", "https://bouldercounty.gov/elections/")
get("boulder_ballot_returns.html", "https://bouldercounty.gov/elections/by-election/2026-general-election/")
# Ballotpedia local RCV pages
get("bp_local_systems.html", "https://ballotpedia.org/Local_electoral_systems_on_the_ballot")
get("bp_rcv_2024.html", "https://ballotpedia.org/Results_for_ranked-choice_voting_(RCV)_and_electoral_system_ballot_measures,_2024")
get("bp_honolulu_measures.html", "https://ballotpedia.org/Honolulu_County,_Hawaii_ballot_measures")
# Hawaii campaign finance (Socrata catalog) and elections
get("hi_socrata_catalog.json", "https://api.us.socrata.com/api/catalog/v1?domains=data.hawaii.gov&q=noncandidate&limit=50")
get("hi_socrata_catalog2.json", "https://api.us.socrata.com/api/catalog/v1?domains=data.hawaii.gov&q=campaign%20spending&limit=50")
get("hi_elections_results.html", "https://elections.hawaii.gov/election-results/")
# Irvine NetFile + OC registrar
get("irvine_netfile_rss.xml", "https://netfile.com/Connect2/api/public/list/filing/rss/IRV/campaign.xml")
get("irvine_netfile_portal.html", "https://public.netfile.com/pub2/?AID=IRV")
get("ocvote_home.html", "https://www.ocvote.gov/")
get("ocvote_data.html", "https://www.ocvote.gov/data")
(OUT / "_log.txt").write_text("\n".join(log))
print("\n".join(log))
