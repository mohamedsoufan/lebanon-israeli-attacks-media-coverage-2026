"""
Stage 1, step 4: identify candidate fatal-attack reports.
Retain articles containing >=1 Israeli-attack indicator AND >=1 death indicator,
searching title + body together (not title alone).
This is an automated filter that produces candidates only -- it does not
make the final include/exclude decision (that's step 5, done separately).
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

ATTACK_INDICATORS = [
    "إسرائيلي", "العدو", "الطيران المعادي", "غارة", "مسيرة",
    "قصف", "مدفعية", "استهداف",
]
DEATH_INDICATORS = [
    "شهيد", "شهداء", "استشهاد", "استشهد", "ارتقاء", "قضى",
    "قتيل", "قتلى", "مقتل", "وفاة",
]


def main():
    with (PROCESSED_DIR / "articles.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} articles loaded")

    candidates = []
    for row in rows:
        text = f"{row.get('title', '')} {row.get('body', '')}"
        attack_hits = [w for w in ATTACK_INDICATORS if w in text]
        death_hits = [w for w in DEATH_INDICATORS if w in text]
        if attack_hits and death_hits:
            row = dict(row)
            row["attack_indicators_matched"] = ";".join(attack_hits)
            row["death_indicators_matched"] = ";".join(death_hits)
            candidates.append(row)

    print(f"{len(candidates)} candidates matched (attack indicator AND death indicator)")

    out_path = PROCESSED_DIR / "candidates.csv"
    fieldnames = ["article_id", "article_url", "lastmod", "publication_datetime",
                  "title", "body", "category", "attack_indicators_matched", "death_indicators_matched"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(candidates, key=lambda r: int(r["article_id"])):
            writer.writerow(row)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
