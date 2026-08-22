import csv, datetime as dt, os, re, time
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api


def with_retry(fn, max_attempts=6):
    delay = 4.0
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and attempt < max_attempts - 1:
                time.sleep(delay)
                delay = min(delay * 1.8, 25)
                continue
            raise
    return None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
COLLECTION_ID = 9272347

with open(BASE_DIR / "data" / "processed" / "pilot_v2_results_full.csv", encoding="utf-8-sig") as f:
    rows = {r["location_day_id"]: r for r in csv.DictReader(f)}

CASES = [
    ("LD-2026-03-08-الدوير (Al-Dawir)", dt.date(2026, 3, 8)),
    ("LD-2026-03-13-النبطية (Nabatieh city)", dt.date(2026, 3, 13)),
    ("LD-2026-03-24-Burj al-Shamali road", dt.date(2026, 3, 24)),
    ("LD-2026-03-24-حلتا (Halta)", dt.date(2026, 3, 24)),
    ("LD-2026-03-24-الشبريحة (Shabriha junction)", dt.date(2026, 3, 24)),
    ("LD-2026-03-28-جويا (Joya)", dt.date(2026, 3, 28)),
]

with (BASE_DIR / "scripts" / "22_casualty_bug_check.progress.log").open("w", encoding="utf-8") as log:
    for ldid, event_date in CASES:
        r = rows.get(ldid)
        if not r:
            log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')}: NOT IN RESULTS\n")
            continue
        query = r["query_used"]
        end3 = event_date + dt.timedelta(days=3)
        try:
            page, _ = with_retry(lambda: search.story_list(query, start_date=event_date, end_date=end3, collection_ids=[COLLECTION_ID], page_size=10))
        except Exception as e:
            log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')}: ERROR {e}\n")
            time.sleep(2)
            continue
        time.sleep(1.5)
        log.write(f"=== {ldid.encode('ascii','backslashreplace').decode('ascii')} (confirming_url={r['confirming_url']}) ===\n")
        for s in page:
            marker = " <-- CONFIRMING URL" if s.get("url") == r["confirming_url"] else ""
            log.write(f"  [{s.get('media_name','')}] {s.get('title','').encode('ascii','backslashreplace').decode('ascii')}{marker}\n")
        log.write("\n")
