"""Download real federal contract award records from USAspending for the entity layer.

Scope (see README): recipients located in California, contracts (award types A-D),
NAICS groups 2382 (building equipment contractors: HVAC, plumbing, electrical),
6211/6212/6213 (offices of physicians, dentists, other health practitioners),
5613 (employment services / staffing), action dates FY2008 through FY2026.
No API key is required. Output: the untouched zip in sources/usaspending/.
"""
import json, sys, time, urllib.request, pathlib, datetime

API = "https://api.usaspending.gov/api/v2"
OUT = pathlib.Path(__file__).resolve().parent.parent / "sources" / "usaspending"
FILTERS = {
    "recipient_locations": [{"country": "USA", "state": "CA"}],
    "naics_codes": {"require": ["2382", "6211", "6212", "6213", "5613"]},
    "award_type_codes": ["A", "B", "C", "D"],
    "time_period": [{"start_date": "2007-10-01", "end_date": "2026-09-30"}],
}

def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    job = post("/download/awards/", {"filters": FILTERS, "file_format": "csv"})
    (OUT / "download_request.json").write_text(json.dumps(
        {"requested_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
         "endpoint": API + "/download/awards/", "filters": FILTERS, "response": job}, indent=2))
    name = job["file_name"]
    while True:
        st = json.load(urllib.request.urlopen(
            f"{API}/download/status/?file_name={name}", timeout=120))
        print(st.get("status"), st.get("total_rows"), flush=True)
        if st["status"] == "finished":
            break
        if st["status"] == "failed":
            sys.exit("download failed: " + json.dumps(st))
        time.sleep(15)
    urllib.request.urlretrieve(st["file_url"], OUT / name)
    meta = json.loads((OUT / "download_request.json").read_text())
    meta["file_url"] = st["file_url"]
    meta["total_rows"] = st.get("total_rows")
    (OUT / "download_request.json").write_text(json.dumps(meta, indent=2))
    print("saved", OUT / name, st["file_url"])

if __name__ == "__main__":
    main()
