import os, json, datetime as dt
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
page, _ = search.story_list('"Jnah" AND Lebanon', start_date=dt.date(2026, 3, 13), end_date=dt.date(2026, 3, 16), collection_ids=[9272347])
out_path = BASE_DIR / "scripts" / "field_check_output.json"
with out_path.open("w", encoding="utf-8") as f:
    json.dump({"n": len(page), "keys": list(page[0].keys()) if page else [], "sample": page[:2]}, f, indent=2, ensure_ascii=False, default=str)
print("wrote", out_path)
