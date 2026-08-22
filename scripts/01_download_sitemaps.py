"""
Stage 1, step 2: download daily NNA sitemaps for the research window
(2026-03-02 through 2026-04-02, to catch delayed reports of March attacks),
extract <loc>/<lastmod>, normalize the localhost URLs, and write a
deduplicated master URL list.
"""
import datetime as dt
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
SITEMAP_DIR = BASE_DIR / "data" / "raw" / "sitemaps"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SITEMAP_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = dt.date(2026, 3, 2)
END_DATE = dt.date(2026, 4, 2)  # inclusive, catches delayed reports
SITEMAP_URL = "https://www.nna-leb.gov.lb/ar/sitemap/n/3?date={date}"
OLD_HOST = "http://localhost:3000"
NEW_HOST = "https://www.nna-leb.gov.lb"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
})

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
ARTICLE_ID_RE = re.compile(r"/ar/news/(\d+)/")


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def fetch_sitemap(date_str: str) -> str | None:
    cache_path = SITEMAP_DIR / f"{date_str}.xml"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    url = SITEMAP_URL.format(date=date_str)
    resp = SESSION.get(url, timeout=30)
    if resp.status_code != 200:
        print(f"  WARN {date_str}: HTTP {resp.status_code}")
        return None
    cache_path.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_sitemap(xml_text: str):
    entries = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  WARN: XML parse error: {e}")
        return entries
    for url_el in root.findall("sm:url", NS):
        loc_el = url_el.find("sm:loc", NS)
        lastmod_el = url_el.find("sm:lastmod", NS)
        if loc_el is None or loc_el.text is None:
            continue
        loc = loc_el.text.strip().replace(OLD_HOST, NEW_HOST)
        lastmod = lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None
        m = ARTICLE_ID_RE.search(loc)
        article_id = m.group(1) if m else None
        entries.append({"article_id": article_id, "article_url": loc, "lastmod": lastmod})
    return entries


def main():
    all_entries = {}  # article_id -> entry (dedup, keep latest lastmod seen)
    no_id_entries = []
    for d in daterange(START_DATE, END_DATE):
        date_str = d.isoformat()
        print(f"Fetching sitemap for {date_str} ...")
        xml_text = fetch_sitemap(date_str)
        if xml_text is None:
            continue
        entries = parse_sitemap(xml_text)
        print(f"  {len(entries)} entries")
        for e in entries:
            if e["article_id"] is None:
                no_id_entries.append(e)
                continue
            aid = e["article_id"]
            if aid not in all_entries or (e["lastmod"] or "") > (all_entries[aid]["lastmod"] or ""):
                all_entries[aid] = e
        time.sleep(0.3)

    print(f"\nTotal unique article IDs: {len(all_entries)}")
    if no_id_entries:
        print(f"WARN: {len(no_id_entries)} sitemap entries had no parseable article_id")

    out_path = PROCESSED_DIR / "sitemap_urls.csv"
    import csv
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["article_id", "article_url", "lastmod"])
        writer.writeheader()
        for aid in sorted(all_entries, key=lambda x: int(x)):
            writer.writerow(all_entries[aid])
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
