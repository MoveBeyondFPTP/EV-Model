"""Temporary: second look at reachable sources and alternate hosts."""
import re, requests, io, zipfile
H = {"User-Agent": "Mozilla/5.0 (EV-Model research; github.com/MoveBeyondFPTP/EV-Model)"}
pat = re.compile(r'href=["\']([^"\']+)["\']', re.I)
def show(name, u, head=0, links=True, filt=None):
    try:
        r = requests.get(u, headers=H, timeout=90)
        print(f"\n=== {name}  {u}  -> {r.status_code} {len(r.content)}B {r.headers.get('content-type')}")
        if head:
            print(r.content[:head].decode("utf-8", "replace"))
        if links and "html" in (r.headers.get("content-type") or ""):
            seen = []
            for l in pat.findall(r.text):
                if (filt is None or re.search(filt, l, re.I)) and l not in seen: seen.append(l)
            for l in seen[:80]: print("  ", l)
        return r
    except Exception as e:
        print(f"\n=== {name}  {u}  !! {e!r}")
F = r"\.(csv|xlsx?|zip|json|txt|pdf)|absentee|early|ballot|stat|report"
show("ME early reports", "https://www.maine.gov/sos/elections-voting/voter-data/early-voting-reports", filt=F)
show("ME previous absentee", "https://www.maine.gov/sos/elections-voting/voter-data/previous-absentee-data", filt=F)
show("ME layout", "https://www.maine.gov/sos/elections-voting/absenteelayout", head=0, links=False)
r = show("ME AB file", "https://www.maine.gov/sos/sites/maine.gov.sos/files/inline-files/11-3-26%20AB%20Voter%20File%20as%20of%2010-27-26.txt", head=1500, links=False)
if r is not None and r.ok:
    lines = r.text.splitlines(); print("ME lines:", len(lines))
for k in ["VbmProvided", "VbmVoted", "EarlyVoted"]:
    show("FL " + k, f"https://electionfiles.floridados.gov/countyballotreportfiles/Stats_49894_{k}.txt", head=1500, links=False)
show("FL dos archive", "https://dos.fl.gov/elections/data-statistics/elections-data/absentee-and-early-voting/", filt=F)
show("FL PublicStats", "https://countyfilesvbm-ev.floridados.gov/VoteByMailEarlyVotingReports/PublicStats", head=0, filt=r"election|select|option")
r = requests.get("https://countyfilesvbm-ev.floridados.gov/VoteByMailEarlyVotingReports/PublicStats", headers=H, timeout=60)
print("FL options:", re.findall(r"<option[^>]*value=\"([^\"]*)\"[^>]*>([^<]*)<", r.text)[:40])
print("FL stats ids:", sorted(set(re.findall(r"Stats_(\d+)_", r.text))))
for name, u in {"AK http": "http://www.elections.alaska.gov/research/absentee-and-early-voting-statistics/",
                "GA hub": "https://sos.ga.gov/election-data-hub-turnout", "GA sos": "https://sos.ga.gov/page/election-data-hub",
                "TX old": "https://www.sos.state.tx.us/elections/earlyvoting/index.shtml",
                "CO alt xlsx": "https://www.sos.state.co.us/pubs/newsRoom/pressReleases/2024/20241028ElectionActivity.xlsx",
                "MI mvic": "https://mvic.sos.state.mi.us/", "NE elections": "https://sos.nebraska.gov/elections",
                "KS results": "https://sos.ks.gov/elections/election-results.html",
                "WI files": "https://elections.wi.gov/sites/default/files/"}.items():
    show(name, u, filt=F)
