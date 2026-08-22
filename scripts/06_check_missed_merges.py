"""
QA pass: scan classification notes for explicit article-ID cross-references
(e.g. "update to 418675 chain", "confirms 418284") and flag any case where
the referenced article ended up in a DIFFERENT incident group than the
article whose notes mention it. These are missed merges caused by
inconsistent town-string spelling or cross-midnight event_date drift.
"""
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

ID_RE = re.compile(r"\b(4[12][0-9]{4})\b")


def main():
    with (PROCESSED_DIR / "incident_updates.csv").open(encoding="utf-8-sig") as f:
        updates = list(csv.DictReader(f))

    article_to_incident = {r["article_id"].rstrip("abcdefghij"): r["incident_id"] for r in updates}
    article_to_notes = {r["article_id"]: r["notes"] for r in updates}

    flagged = []
    for r in updates:
        aid = r["article_id"]
        notes = r["notes"] or ""
        refs = set(ID_RE.findall(notes))
        refs.discard(aid.rstrip("abcdefghij"))
        for ref in refs:
            ref_incident = article_to_incident.get(ref)
            if ref_incident and ref_incident != r["incident_id"]:
                flagged.append((r["incident_id"], aid, ref_incident, ref, notes))

    out_path = PROCESSED_DIR / "_missed_merge_candidates.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for inc, aid, ref_inc, ref, notes in flagged:
            f.write(f"{inc} ({aid}) references {ref} which is in {ref_inc}\n  notes: {notes}\n\n")
    print(f"{len(flagged)} potential missed merges written to {out_path}")


if __name__ == "__main__":
    main()
