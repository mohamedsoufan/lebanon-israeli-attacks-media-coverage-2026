import csv, datetime as dt, os
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
COLLECTION_ID = 9272347

# Test whether adding the Guardian's spelling "Al-Nimiriya" (not in the current
# alias list: Nmeiriyeh;Numeiriyeh;Al-Nmeiriyeh) would find coverage the current
# alias set missed, for the Mar 9 Nmeiriyeh (15 deaths) location-day.
query_current = '("Nmeiriyeh" OR "Numeiriyeh" OR "Al-Nmeiriyeh") AND Lebanon'
query_alt = '("Al-Nimiriya" OR "Nimiriya") AND Lebanon'

start = dt.date(2026, 3, 9)
end3 = start + dt.timedelta(days=3)

with (BASE_DIR / "scripts" / "20_alias_adequacy.progress.log").open("w", encoding="utf-8") as log:
    for label, q in [("current_aliases", query_current), ("alt_spelling", query_alt)]:
        page, _ = search.story_list(q, start_date=start, end_date=end3, collection_ids=[COLLECTION_ID], page_size=10)
        log.write(f"{label}: query={q}\n  n={len(page)}\n")
        for s in page[:10]:
            log.write(f"  [{s.get('media_name','')}] {s.get('title','').encode('ascii','backslashreplace').decode('ascii')} | {s.get('url','')}\n")
        log.write("\n")
