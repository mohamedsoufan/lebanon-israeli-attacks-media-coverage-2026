"""
Stage 2 pilot: run Media Cloud searches for a stratified set of location-days,
log every query/result to media_search_log.csv, and dump the raw returned
stories (title, outlet, url, publish date, language) to a per-location-day
file for manual relevance classification.
"""
import csv
import datetime as dt
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_RESULTS_DIR = PROCESSED_DIR / "media_search_raw"
RAW_RESULTS_DIR.mkdir(exist_ok=True)
PROGRESS_LOG = BASE_DIR / "scripts" / "12_pilot_search.progress.log"

load_dotenv()
API_KEY = os.environ["MEDIACLOUD_API_KEY"]
COLLECTION_ID = 9272347  # Global English Language Sources - see media_source_universe.csv

LEBANON_TERM = "Lebanon"

LOG_FIELDS = [
    "location_day_id", "location", "event_date", "aliases_used", "is_ambiguous",
    "collection_ids", "query", "search_start", "search_end_3d", "search_end_7d",
    "result_count_3d", "result_count_7d", "stories_returned_3d", "api_status",
    "raw_results_file", "timestamp",
]


def load_aliases():
    with (PROCESSED_DIR / "location_aliases.csv").open(encoding="utf-8-sig") as f:
        return {r["location"]: r for r in csv.DictReader(f)}


def load_location_days():
    with (PROCESSED_DIR / "location_day.csv").open(encoding="utf-8-sig") as f:
        return {r["location_day_id"]: r for r in csv.DictReader(f)}


def build_query(aliases, is_ambiguous):
    alias_clause = " OR ".join(f'"{a}"' for a in aliases)
    q = f"({alias_clause}) AND {LEBANON_TERM}"
    if is_ambiguous == "1":
        q += ' AND (strike OR airstrike OR raid OR killed OR attack OR shelling)'
    return q


def already_logged_ids(log_path):
    if not log_path.exists():
        return set()
    with log_path.open(encoding="utf-8-sig") as f:
        return {r["location_day_id"] for r in csv.DictReader(f)}


def append_log_row(log_path, row):
    file_exists = log_path.exists()
    with log_path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def progress(msg):
    with PROGRESS_LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def main(pilot_ids_file):
    aliases = load_aliases()
    ld = load_location_days()

    with open(pilot_ids_file, encoding="utf-8") as f:
        pilot_ids = [line.strip() for line in f if line.strip()]

    log_path = PROCESSED_DIR / "media_search_log.csv"
    done_ids = already_logged_ids(log_path)

    search = mediacloud.api.SearchApi(API_KEY)

    for ldid in pilot_ids:
        if ldid in done_ids:
            progress(f"SKIP (already logged): {ldid}")
            continue

        row = ld[ldid]
        loc = row["location"]
        alias_row = aliases.get(loc)
        if not alias_row:
            progress(f"WARN: no aliases for {loc}")
            continue
        alias_list = alias_row["aliases"].split(";")
        is_amb = alias_row["is_ambiguous_common_word"]
        query = build_query(alias_list, is_amb)

        event_date = dt.date.fromisoformat(row["event_date"])
        start = event_date
        end = event_date + dt.timedelta(days=3)
        end7 = event_date + dt.timedelta(days=7)

        api_status = "ok"
        stories = []
        count_3d = None
        count_7d = None
        try:
            count_3d = search.story_count(query, start_date=start, end_date=end, collection_ids=[COLLECTION_ID])["relevant"]
        except Exception as e:
            api_status = f"error: {type(e).__name__}: {e}"

        if api_status == "ok":
            try:
                page, _ = search.story_list(query, start_date=start, end_date=end, collection_ids=[COLLECTION_ID])
                stories = page or []
            except Exception as e:
                api_status = f"story_list error: {type(e).__name__}: {e}"

        try:
            count_7d = search.story_count(query, start_date=start, end_date=end7, collection_ids=[COLLECTION_ID])["relevant"]
        except Exception:
            count_7d = None

        # dump raw stories for manual classification
        raw_path = RAW_RESULTS_DIR / f"{ldid.replace('/', '_')}.csv"
        with raw_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["title", "media_name", "media_url", "url", "publish_date", "language", "indexed_date"])
            for s in stories:
                w.writerow([
                    s.get("title", ""),
                    (s.get("media_name") or ""),
                    (s.get("media_url") or ""),
                    s.get("url", ""),
                    s.get("publish_date", ""),
                    s.get("language", ""),
                    s.get("indexed_date", ""),
                ])

        log_row = {
            "location_day_id": ldid,
            "location": loc,
            "event_date": row["event_date"],
            "aliases_used": ";".join(alias_list),
            "is_ambiguous": is_amb,
            "collection_ids": str(COLLECTION_ID),
            "query": query,
            "search_start": str(start),
            "search_end_3d": str(end),
            "search_end_7d": str(end7),
            "result_count_3d": count_3d if count_3d is not None else "",
            "result_count_7d": count_7d if count_7d is not None else "",
            "stories_returned_3d": len(stories),
            "api_status": api_status,
            "raw_results_file": str(raw_path.relative_to(BASE_DIR)),
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        }
        append_log_row(log_path, log_row)
        progress(f"DONE: {ldid.encode('ascii', 'backslashreplace').decode('ascii')} | status={api_status} | 3d={count_3d} | 7d={count_7d} | stories={len(stories)}")
        time.sleep(0.5)

    progress(f"--- run complete: {len(pilot_ids)} pilot ids processed (see media_search_log.csv for results) ---")


if __name__ == "__main__":
    main(sys.argv[1])
