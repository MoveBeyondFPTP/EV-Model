import io, requests, zipfile
import pandas as pd
H = {"User-Agent": "Mozilla/5.0 (compatible; EV-Model/1.0; +https://github.com/MoveBeyondFPTP/EV-Model)"}
B = "https://assets01.aws.connect.clarityelections.com/Assets/Connect/RootPublish/dallas-tx.connect.clarityelections.com/ElectionDocuments/2022/2022%20General%20and%20Joint/"
for f in ["Early-Voting-Turnout-By-Date-Location-Report-11.04.22.xlsx", "In-Person-Early-Voting-Report-11.04.22.xlsx"]:
    r = requests.get(B + f, headers=H, timeout=60)
    print("\n==", f, r.status_code, r.headers.get("content-type"), len(r.content)); print(repr(r.content[:300]))
    if r.content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(r.content)); print(z.namelist()[:20])
        try:
            x = pd.read_excel(io.BytesIO(r.content), header=None, engine="openpyxl"); print(x.shape); print(x.head(8).to_string()[:2500])
        except Exception as e:
            print("openpyxl:", repr(e))
