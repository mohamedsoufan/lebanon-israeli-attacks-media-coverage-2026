"""
Stage 1, step 3: scrape every listed article via NNA's article JSON endpoint
(https://www.nna-leb.gov.lb/api/proxy/v2/ar/news/{id}), caching raw JSON per
article and writing a flat articles.csv with article_id, article_url,
publication_datetime, title, body.
"""
import csv
import html
import json
import re
import time
from pathlib import Path

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
ARTICLES_DIR = BASE_DIR / "data" / "raw" / "articles"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://www.nna-leb.gov.lb/api/proxy/v2/ar/news/{id}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def fetch_one(article_id: str, session: requests.Session):
    cache_path = ARTICLES_DIR / f"{article_id}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # corrupt cache, refetch
    url = API_URL.format(id=article_id)
    resp = session.get(url, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "article_id": article_id}
    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return {"error": "bad JSON", "article_id": article_id}
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def main():
    with (PROCESSED_DIR / "sitemap_urls.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} articles to fetch (cached ones will be skipped)")

    session = requests.Session()
    results = {}
    errors = []

    def worker(row):
        aid = row["article_id"]
        payload = fetch_one(aid, session)
        return aid, row, payload

    # modest concurrency, polite to the server
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(worker, row) for row in rows]
        done = 0
        for fut in as_completed(futures):
            aid, row, payload = fut.result()
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(rows)} fetched")
            if not payload or "error" in payload:
                errors.append((aid, payload.get("error") if payload else "no payload"))
                continue
            node = payload.get("data", {}).get("data", payload.get("data", payload))
            results[aid] = {
                "article_id": aid,
                "article_url": row["article_url"],
                "lastmod": row["lastmod"],
                "publication_datetime": node.get("added_at"),
                "title": node.get("title", ""),
                "body": strip_html(node.get("content", "")),
                "category": (node.get("category") or {}).get("name") if isinstance(node.get("category"), dict) else node.get("category"),
            }
            time.sleep(0.02)

    print(f"\nFetched OK: {len(results)}  Errors: {len(errors)}")
    if errors:
        err_path = PROCESSED_DIR / "fetch_errors.csv"
        with err_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["article_id", "error"])
            w.writerows(errors)
        print(f"Wrote errors to {err_path}")

    out_path = PROCESSED_DIR / "articles.csv"
    fieldnames = ["article_id", "article_url", "lastmod", "publication_datetime", "title", "body", "category"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for aid in sorted(results, key=lambda x: int(x)):
            writer.writerow(results[aid])
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
