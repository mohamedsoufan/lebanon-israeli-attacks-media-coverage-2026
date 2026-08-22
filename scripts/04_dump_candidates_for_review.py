"""
Formats candidates.csv into numbered, readable text blocks for manual
classification (Stage 1 step 5). Splits into batches so each can be read
and classified in one pass.
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REVIEW_DIR = PROCESSED_DIR / "review_batches"
REVIEW_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 40

with (PROCESSED_DIR / "candidates.csv").open(encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i:i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    out_path = REVIEW_DIR / f"batch_{batch_num:02d}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for r in batch:
            f.write(f"=== ARTICLE_ID: {r['article_id']} ===\n")
            f.write(f"URL: {r['article_url']}\n")
            f.write(f"PUBLISHED: {r['publication_datetime']}\n")
            f.write(f"CATEGORY: {r['category']}\n")
            f.write(f"TITLE: {r['title']}\n")
            f.write(f"BODY: {r['body']}\n")
            f.write("\n")
    print(f"Wrote {out_path} ({len(batch)} articles)")

print(f"\nTotal candidates: {len(rows)} in {(len(rows) + BATCH_SIZE - 1)//BATCH_SIZE} batches")
