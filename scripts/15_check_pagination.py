import os, datetime as dt
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])

query = '("Nabi Chit" OR "Nabi Sheet" OR "Nabi Shit") AND Lebanon'
page, token = search.story_list(query, start_date=dt.date(2026, 3, 6), end_date=dt.date(2026, 3, 9), collection_ids=[9272347])
count = search.story_count(query, start_date=dt.date(2026, 3, 6), end_date=dt.date(2026, 3, 9), collection_ids=[9272347])

with (BASE_DIR / "scripts" / "15_check_pagination.progress.log").open("w", encoding="utf-8") as f:
    f.write(f"page_len={len(page)}\n")
    f.write(f"pagination_token={token}\n")
    f.write(f"story_count relevant={count.get('relevant')} total={count.get('total')}\n")
