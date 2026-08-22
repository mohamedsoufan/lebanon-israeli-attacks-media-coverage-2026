"""
Audit: find every included report whose text signals the attack happened
before the article's publish date (cross-midnight / retrospective language),
and flag whether the recorded event_date already accounts for it.
"""
import csv
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ARTICLES_DIR = BASE_DIR / "data" / "raw" / "articles"

# Arabic markers signaling the event occurred before the calendar day of publication
RETRO_MARKERS = [
    "أمس",              # yesterday
    "الليلة الماضية",     # last night
    "ليلة أمس",
    "الليل الماضي",
    "قبل يومين",
    "منذ يومين",
    "ليل الاثنين",       # "night of <day>-<day>" constructions (cross-midnight)
    "ليل الثلاثاء",
    "ليل الأربعاء",
    "ليل الاربعاء",
    "ليل الخميس",
    "ليل الجمعة",
    "ليل السبت",
    "ليل الأحد",
    "ليل السبت",
]

# explicit date stamp pattern e.g. "بتاريخ 17/3/2026" or "17 /3 /2026"
DATE_STAMP_RE = re.compile(r"بتاريخ\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")


def load_article(article_id):
    p = ARTICLES_DIR / f"{article_id}.json"
    if not p.exists():
        return None
    payload = json.loads(p.read_text(encoding="utf-8"))
    node = payload.get("data", {}).get("data", payload.get("data", payload))
    return node.get("title", "") + " " + (node.get("content") or "")


def main():
    with (PROCESSED_DIR / "candidates_classified.csv").open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["include"] == "1"]
    with (PROCESSED_DIR / "articles.csv").open(encoding="utf-8-sig") as f:
        articles = {r["article_id"]: r for r in csv.DictReader(f)}

    flagged = []
    for r in rows:
        base = r["article_id"].rstrip("abcdefghij")
        art = articles.get(base)
        if not art:
            continue
        text = load_article(base) or ""
        markers_hit = [m for m in RETRO_MARKERS if m in text]
        date_stamp = DATE_STAMP_RE.search(text)
        publish_date = art["lastmod"][:10]
        stamp_date = None
        if date_stamp:
            d, m, y = date_stamp.groups()
            stamp_date = f"{y}-{int(m):02d}-{int(d):02d}"
        if markers_hit or (stamp_date and stamp_date != r["event_date"]):
            flagged.append({
                "article_id": r["article_id"],
                "recorded_event_date": r["event_date"],
                "publish_date": publish_date,
                "markers": ";".join(markers_hit),
                "explicit_date_stamp": stamp_date or "",
                "time_field": r["event_time_if_known"],
                "town": r["town"],
            })

    out_path = PROCESSED_DIR / "_retrospective_scan.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(flagged[0].keys()))
        w.writeheader()
        w.writerows(flagged)
    print(f"{len(flagged)} rows flagged for retrospective/cross-midnight language, written to {out_path}")


if __name__ == "__main__":
    main()
