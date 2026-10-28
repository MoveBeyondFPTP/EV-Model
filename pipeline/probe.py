"""Temporary: which county early-vote sources are reachable from GitHub's servers?"""
import re, requests, concurrent.futures as cf
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
URLS = {
 "TX Bexar": "https://earlyvotecountsdual.bexar.org",
 "TX Harris": "https://www.harrisvotes.com/",
 "TX Harris EV": "https://www.harrisvotes.com/Voter/Early-Voting",
 "TX Travis": "https://votetravis.gov/",
 "TX Tarrant": "https://www.tarrantcountytx.gov/en/elections.html",
 "TX Dallas": "https://www.dallascountyvotes.org/",
 "TX Collin": "https://www.collincountytx.gov/Elections",
 "TX ElPaso": "https://epcountyvotes.com/",
 "MN sos.mn.gov": "https://sos.mn.gov/election-administration-campaigns/data-maps/absentee-data",
 "IA file": "https://sos.iowa.gov/sites/default/files/2026-06/ABS%20Congressional%202026.pdf",
 "KS JoCo": "https://www.jocoelection.org/",
 "KS Sedgwick": "https://www.sedgwickcounty.org/elections/",
 "NE Douglas": "https://www.votedouglascounty.com/",
 "NE Lancaster": "https://www.lancaster.ne.gov/434/Election-Commissioner",
 "WI Milwaukee": "https://city.milwaukee.gov/election",
 "WI Madison": "https://www.cityofmadison.com/clerk/elections-voting/data",
 "WI Dane": "https://elections.countyofdane.com/",
 "MI Detroit": "https://detroitmi.gov/government/city-clerk/elections",
 "MI Oakland": "https://www.oakgov.com/government/clerk-register-of-deeds/elections",
 "GA Fulton": "https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/registration-and-elections",
 "GA Cobb": "https://www.cobbcounty.gov/elections",
 "GA Gwinnett": "https://www.gwinnettcounty.com/government/departments/elections",
 "GA DeKalb": "https://www.dekalbcountyga.gov/voter-registration-elections",
 "CO Denver": "https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Denver-Elections-Division",
 "CO ElPaso": "https://clerkandrecorder.elpasoco.com/elections/",
 "CO Jeffco": "https://www.jeffco.us/elections",
 "CO Arapahoe": "https://www.arapahoevotes.gov/",
 "NH Manchester": "https://www.manchesternh.gov/Departments/City-Clerk/Elections",
}
pat = re.compile(r'href=["\']([^"\']+)["\']', re.I)
KEY = re.compile(r"early|turnout|absentee|ballot|return|advance|roster|statistic|report|\.(csv|xlsx?|pdf|json|zip)", re.I)
def check(item):
    name, u = item
    try:
        r = requests.get(u, headers=H, timeout=(15, 45), allow_redirects=True)
        ct = r.headers.get("content-type", "")
        blocked = any(s in r.text[:3000] for s in ("Just a moment", "Attention Required", "Access Denied", "cf-chl", "Request unsuccessful"))
        out = [f"\n=== {name} {u} -> {r.status_code} {len(r.content)}B {ct.split(';')[0]} final={r.url}{'  [BLOCKED]' if blocked else ''}"]
        if "html" in ct and not blocked:
            t = re.search(r"<title>(.*?)</title>", r.text, re.I | re.S)
            out.append("  title: " + (t.group(1).strip()[:100] if t else ""))
            seen = []
            for l in pat.findall(r.text):
                if KEY.search(l) and l not in seen and not l.startswith("#"): seen.append(l)
            out += ["   " + l for l in seen[:35]]
        return "\n".join(out)
    except Exception as e:
        return f"\n=== {name} {u} !! {e!r}"
with cf.ThreadPoolExecutor(8) as ex:
    for res in ex.map(check, URLS.items()):
        print(res, flush=True)
