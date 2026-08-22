import csv, datetime as dt
from pathlib import Path
import os
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = PROCESSED_DIR / "media_search_raw"
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
COLLECTION_ID = 9272347

CASES = [
    {
        "ldid": "LD-2026-03-18-بيروت (Beirut)",
        "event_date": dt.date(2026, 3, 18),
        "query": '("Basta" OR "al-Basta" OR "Zuqaq al-Blat" OR "Zokak el-Blat") AND Lebanon',
    },
    {
        "ldid": "LD-2026-03-08-صور (Tyre)",
        "event_date": dt.date(2026, 3, 8),
        "query": '("Al-Athar" OR "Athar neighborhood") AND (Tyre OR Sour) AND Lebanon',
    },
    {
        "ldid": "LD-2026-03-05-أوتوستراد زحلة الكرك (Zahle-Kark highway)",
        "event_date": dt.date(2026, 3, 5),
        "query": '("Zahle-Kark highway" OR "Zahle-Karak highway") AND Lebanon AND (vehicle OR car)',
    },
]

with (BASE_DIR / "scripts" / "17_generic_location_search.progress.log").open("w", encoding="utf-8") as log:
    for case in CASES:
        start = case["event_date"]
        end3 = start + dt.timedelta(days=3)
        end7 = start + dt.timedelta(days=7)
        count3 = search.story_count(case["query"], start_date=start, end_date=end3, collection_ids=[COLLECTION_ID])
        page3, _ = search.story_list(case["query"], start_date=start, end_date=end3, collection_ids=[COLLECTION_ID], page_size=10)
        count7 = search.story_count(case["query"], start_date=start, end_date=end7, collection_ids=[COLLECTION_ID])

        out_path = RAW_DIR / f"generic_{case['ldid'].replace('/', '_')}.csv"
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["title", "media_name", "url", "publish_date"])
            for s in page3:
                w.writerow([s.get("title", ""), s.get("media_name", ""), s.get("url", ""), s.get("publish_date", "")])

        log.write(f"{case['ldid'].encode('ascii','backslashreplace').decode('ascii')}\n")
        log.write(f"  query: {case['query']}\n")
        log.write(f"  count_3d relevant={count3.get('relevant')} | count_7d relevant={count7.get('relevant')}\n")
        for i, s in enumerate(page3[:10], 1):
            log.write(f"  {i}. [{s.get('media_name','')}] {s.get('title','').encode('ascii','backslashreplace').decode('ascii')} | {s.get('url','')}\n")
        log.write("\n")
