"""Temporary: check which state early-vote sources are reachable and what they link to."""
import re, requests
H = {"User-Agent": "Mozilla/5.0 (EV-Model research; github.com/MoveBeyondFPTP/EV-Model)"}
URLS = {
 "FL stats": "https://countyballotfiles.floridados.gov/VoteByMailEarlyVotingReports/PublicStats",
 "FL stats2": "https://countyfilesvbm-ev.floridados.gov/VoteByMailEarlyVotingReports/PublicStats",
 "GA absentee": "https://elections.sos.ga.gov/Elections/voterabsenteefile.do",
 "TX ev": "https://earlyvoting.texas-election.com/",
 "WI absentee": "https://elections.wi.gov/statistics-data/absentee-ballot-reports",
 "WI absentee2": "https://elections.wi.gov/taxonomy/term/306",
 "MI dashboard": "https://www.michigan.gov/sos/elections/voting-dashboard",
 "CO returns 2026": "https://www.coloradosos.gov/pubs/newsRoom/pressReleases/2026/PR20261026BallotReturns.html",
 "CO returns 2022": "https://coloradosos.gov/pubs/newsRoom/pressReleases/2022/PR20221031BallotReturns.html",
 "IA absentee": "https://sos.iowa.gov/elections/results/absenteestats.html",
 "IA absentee2": "https://sos.iowa.gov/elections/electionresults/absenteestats.html",
 "KS advance": "https://sos.ks.gov/elections/elections-statistics-data.html",
 "NE": "https://sos.nebraska.gov/elections/election-statistics",
 "NH": "https://www.sos.nh.gov/elections/elections/election-results",
 "ME absentee": "https://www.maine.gov/sos/cec/elec/data/index.html",
 "AK absentee": "https://www.elections.alaska.gov/election-results/",
 "AK stats": "https://www.elections.alaska.gov/research/absentee-and-early-voting-statistics/",
 "MN absentee": "https://www.sos.state.mn.us/election-administration-campaigns/data-maps/absentee-and-mail-ballot-data/",
}
pat = re.compile(r'href=["\']([^"\']+)["\']', re.I)
for name, u in URLS.items():
    try:
        r = requests.get(u, headers=H, timeout=60)
        print(f"\n=== {name}  {u}  -> {r.status_code} {len(r.content)}B {r.headers.get('content-type')}")
        links = [l for l in pat.findall(r.text) if re.search(r"\.(csv|xlsx?|zip|json|txt|pdf)(\?|$)|download|export|absentee|early|ballot|stat|report|api", l, re.I)]
        seen = []
        for l in links:
            if l not in seen: seen.append(l)
        for l in seen[:60]: print("  ", l)
        if not seen: print("  [text]", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:800])
    except Exception as e:
        print(f"\n=== {name}  {u}  !! {e!r}")
