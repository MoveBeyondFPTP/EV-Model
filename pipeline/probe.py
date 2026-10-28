import io, re, requests
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
B = "https://outside.vermont.gov/dept/sos/Elections_Division/voters/"
names = ["2026_vermont_primary_election_early_voter_turnout_statistics.pdf",
         "2026_vermont_general_election_early_voter_turnout_statistics.pdf",
         "2026_general_election_early_voter_turnout_statistics.pdf",
         "2022_vermont_general_election_early_voter_turnout_statistics.pdf",
         "2024_vermont_general_election_early_voter_turnout_statistics.pdf"]
import pdfplumber
for n in names:
    try:
        r = requests.get(B + n, headers=H, timeout=(15, 60))
        print("\n==", n, r.status_code, r.headers.get("content-type"), len(r.content))
        if r.ok and r.content[:4] == b"%PDF":
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                print(len(pdf.pages), "pages"); print((pdf.pages[0].extract_text() or "")[:1500])
    except Exception as e:
        print(n, repr(e))
for u in ["https://sos.vermont.gov/elections/voters/early-absentee-voting", "https://sos.vermont.gov/secretarys-desk/commentary-press/",
          "https://sos.vermont.gov/elections/election-info-resources/elections-data/", "https://outside.vermont.gov/dept/sos/Elections_Division/voters/"]:
    try:
        r = requests.get(u, headers=H, timeout=(15, 60))
        ls = [l for l in re.findall(r'href=["\']([^"\']+)["\']', r.text) if re.search(r"turnout|early|statistic|\.pdf|\.xlsx|\.csv", l, re.I)]
        print("\n==", u, r.status_code, len(r.content)); [print("  ", l) for l in ls[:40]]
    except Exception as e:
        print(u, repr(e))
