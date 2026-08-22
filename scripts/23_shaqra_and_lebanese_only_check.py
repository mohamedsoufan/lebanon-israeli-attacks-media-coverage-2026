import csv, datetime as dt, os, time
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
COLLECTION_ID = 9272347


def with_retry(fn, max_attempts=7):
    delay = 4.0
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and attempt < max_attempts - 1:
                time.sleep(delay)
                delay = min(delay * 1.8, 30)
                continue
            raise
    return None


with open(BASE_DIR / "data" / "processed" / "pilot_v2_results_full.csv", encoding="utf-8-sig") as f:
    rows = {r["location_day_id"]: r for r in csv.DictReader(f)}

CASES = [
    "LD-2026-03-29-شقرا (Shaqra)",
    "LD-2026-03-09-الطيري (Al-Tiri)",
    "LD-2026-03-10-القليلة (Qlaile)",
    "LD-2026-03-11-كفرتبنيت (Kfartebnit)",
    "LD-2026-03-13-شبعا (Shebaa)",
    "LD-2026-03-15-عيتيت (Aitit)",
    "LD-2026-03-17-طريق المطار (Airport Road)",
    "LD-2026-03-23-عيتيت (Aitit)",
    "LD-2026-03-22-الصوانة (Al-Sawwaneh)",
    "LD-2026-03-27-زوطر الشرقية (Zawtar al-Sharqiya)",
    "LD-2026-03-15-الشرحبيل (Sharhabil)",
]

with (BASE_DIR / "scripts" / "23_shaqra_and_lebanese_only.progress.log").open("w", encoding="utf-8") as log:
    for ldid in CASES:
        r = rows.get(ldid)
        if not r:
            log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')}: NOT FOUND\n")
            continue
        query = r["query_used"].split(" | fallback:")[0].strip()
        if query.startswith("base:"):
            query = query[len("base:"):].strip()
        event_date = dt.date.fromisoformat(r["event_date"])
        end3 = event_date + dt.timedelta(days=3)
        try:
            count = with_retry(lambda: search.story_count(query, start_date=event_date, end_date=end3, collection_ids=[COLLECTION_ID]))
        except Exception as e:
            log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')}: ERROR {e}\n\n")
            continue
        relevant = count.get("relevant") if count else None
        log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')}: true_relevant_count={relevant} | query={query}\n")
        time.sleep(1.5)
