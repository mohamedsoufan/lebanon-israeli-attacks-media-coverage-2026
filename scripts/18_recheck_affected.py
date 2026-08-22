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
        "name": "Tyre_alt1_ruins",
        "ldid": "LD-2026-03-08-صور (Tyre)",
        "event_date": dt.date(2026, 3, 8),
        "query": '("Tyre" OR "Sour") AND Lebanon AND ("8 killed" OR "10 killed" OR ruins OR archaeological OR ancient)',
    },
    {
        "name": "Tyre_alt2_athar_variants",
        "ldid": "LD-2026-03-08-صور (Tyre)",
        "event_date": dt.date(2026, 3, 8),
        "query": '("Al Athar" OR "al-Aathar" OR "Athar area" OR "Hay al-Athar") AND Lebanon',
    },
    {
        "name": "ZahleKark_alt_karak",
        "ldid": "LD-2026-03-05-أوتوستراد زحلة الكرك (Zahle-Kark highway)",
        "event_date": dt.date(2026, 3, 5),
        "query": '("Karak highway" OR "Zahle-Karak" OR "Karak-Zahle") AND Lebanon',
    },
    {
        "name": "NabiChit_Mar6_residential",
        "ldid": "LD-2026-03-06-النبي شيت (Nabi Chit/Nabi Sheet)",
        "event_date": dt.date(2026, 3, 6),
        "query": '("Nabi Chit" OR "Nabi Sheet") AND Lebanon AND (residential OR "10 killed" OR neighborhood OR neighbourhood)',
    },
    {
        "name": "NabiChit_Mar7_commando",
        "ldid": "LD-2026-03-07-النبي شيت (Nabi Chit)",
        "event_date": dt.date(2026, 3, 7),
        "query": '("Nabi Chit" OR "Nabi Sheet") AND Lebanon AND (commando OR "Lebanese Army" OR soldiers OR "26 killed" OR Khirbeh OR Sarain)',
    },
]

with (BASE_DIR / "scripts" / "18_recheck_affected.progress.log").open("w", encoding="utf-8") as log:
    for case in CASES:
        start = case["event_date"]
        end3 = start + dt.timedelta(days=3)
        count3 = search.story_count(case["query"], start_date=start, end_date=end3, collection_ids=[COLLECTION_ID])
        page3, _ = search.story_list(case["query"], start_date=start, end_date=end3, collection_ids=[COLLECTION_ID], page_size=10)

        out_path = RAW_DIR / f"recheck_{case['name']}.csv"
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["title", "media_name", "url", "publish_date"])
            for s in page3:
                w.writerow([s.get("title", ""), s.get("media_name", ""), s.get("url", ""), s.get("publish_date", "")])

        log.write(f"=== {case['name']} ===\n")
        log.write(f"  query: {case['query']}\n")
        log.write(f"  count_3d relevant={count3.get('relevant')}\n")
        for i, s in enumerate(page3[:10], 1):
            log.write(f"  {i}. [{s.get('media_name','')}] {s.get('title','').encode('ascii','backslashreplace').decode('ascii')} | {s.get('url','')}\n")
        log.write("\n")
