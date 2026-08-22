import os, datetime as dt, json
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])

query = '("Airport Road" OR "Beirut Airport Road" OR "Beirut international airport road") AND Lebanon AND (strike OR airstrike OR raid OR killed OR attack OR shelling)'

out_lines = []
for sort_val in ["relevance", "RELEVANCE", "indexed_desc", "INDEXED_DESC", "publish_date_desc"]:
    try:
        page, token = search.story_list(query, start_date=dt.date(2026, 3, 4), end_date=dt.date(2026, 3, 7), collection_ids=[9272347], sort_order=sort_val, page_size=10)
        out_lines.append(f"sort_order={sort_val} -> OK, n={len(page)}, first_title={page[0]['title'] if page else 'NONE'}")
    except Exception as e:
        out_lines.append(f"sort_order={sort_val} -> ERROR: {type(e).__name__}: {e}")

with (BASE_DIR / "scripts" / "16_check_sort.progress.log").open("w", encoding="utf-8") as f:
    f.write("\n".join(out_lines) + "\n")
