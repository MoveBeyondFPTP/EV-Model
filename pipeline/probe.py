"""Temporary: look inside promising county early-vote pages and files."""
import re, io, requests, concurrent.futures as cf
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
def text(html):
    html = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html))
def pdftext(content, pages=2):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return f"[{len(pdf.pages)} pages] " + "\n".join((p.extract_text() or "") for p in pdf.pages[:pages])
KEY = re.compile(r"early|turnout|absentee|ballot|advance|roster|statistic|report|daily|count|\.(csv|xlsx?|pdf|json|zip)", re.I)
URLS = {
 "Bexar": "https://earlyvotecountsdual.bexar.org/",
 "Harris reports": "https://www.harrisvotes.com/Election-Results/Election-Reports",
 "Harris rosters": "https://www.harrisvotes.com/Election-Results/Election-Rosters",
 "Dallas 2026": "https://www.dallascountyvotes.org/election-results/historical/november-3-2026-general-and-joint-election/",
 "Dallas 2022": "https://www.dallascountyvotes.org/election-results/historical/november-8-2022-general-and-joint-election/",
 "Collin stats": "https://www.collincountytx.gov/elections/statistics",
 "Fulton turnout": "https://www.fultoncountyga.gov/Inside-Fulton-County/Fulton-County-Departments/Registration-and-Elections/Early-Voting-Turnout-Information",
 "Fulton AV pdf": "https://www.fultoncountyga.gov/-/media/November-3-Election-Reports/AV-Daily-Count/102626-advance-voting-daily-count.pdf",
 "Douglas NE turnout": "https://www.votedouglascounty-ne.gov/voter_turnout.aspx",
 "Douglas NE early": "https://www.votedouglascounty-ne.gov/early_voting.aspx",
 "Sedgwick reports": "https://www.sedgwickcounty.org/elections/reports/",
 "JoCo advance": "https://www.jocoelection.org/voting-election-info/advance-voting",
 "Milwaukee EV": "https://city.milwaukee.gov/earlyvoting",
 "Travis EV": "https://votetravis.gov/current-election-information/early-voting-turnout/",
 "Tarrant results": "https://www.tarrantcountytx.gov/en/elections/election-results.html",
}
def look(item):
    name, u = item
    try:
        r = requests.get(u, headers=H, timeout=(15, 60))
        ct = r.headers.get("content-type", "")
        out = [f"\n=== {name} {u} -> {r.status_code} {len(r.content)}B {ct.split(';')[0]}"]
        if "pdf" in ct or u.endswith(".pdf"):
            out.append(pdftext(r.content)[:2500])
        else:
            out.append("TEXT: " + text(r.text)[:1800])
            links = []
            for l in re.findall(r'href=["\']([^"\']+)["\']', r.text):
                if KEY.search(l) and l not in links and not l.startswith(("#", "mailto")) and "facebook" not in l: links.append(l)
            out += ["   " + l[:220] for l in links[:45]]
        return "\n".join(out)
    except Exception as e:
        return f"\n=== {name} {u} !! {e!r}"
with cf.ThreadPoolExecutor(8) as ex:
    for res in ex.map(look, URLS.items()):
        print(res, flush=True)
