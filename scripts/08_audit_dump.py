"""
Validation audit helper: for a given incident selection, print each
incident's recorded fields side-by-side with the original article text
(title+body) for every NNA report that feeds it, so the extraction can be
re-checked against source.
"""
import csv
import html
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ARTICLES_DIR = BASE_DIR / "data" / "raw" / "articles"

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_html(raw):
    if not raw:
        return ""
    text = TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def load_article(article_id):
    p = ARTICLES_DIR / f"{article_id}.json"
    if not p.exists():
        return None
    payload = json.loads(p.read_text(encoding="utf-8"))
    node = payload.get("data", {}).get("data", payload.get("data", payload))
    return {
        "title": node.get("title", ""),
        "body": strip_html(node.get("content", "")),
    }


def main():
    selector = sys.argv[1] if len(sys.argv) > 1 else "ambiguous"

    with (PROCESSED_DIR / "incidents.csv").open(encoding="utf-8-sig") as f:
        incs = list(csv.DictReader(f))
    with (PROCESSED_DIR / "incident_updates.csv").open(encoding="utf-8-sig") as f:
        updates = list(csv.DictReader(f))
    upd_by_incident = {}
    for u in updates:
        upd_by_incident.setdefault(u["incident_id"], []).append(u)

    if selector == "ambiguous":
        selected = [i for i in incs if i["location_ambiguous"] == "1" or i["casualty_count_ambiguous"] == "1"]
        out_name = "audit_ambiguous.txt"
    elif selector == "march7":
        selected = [i for i in incs if i["event_date"] == "2026-03-07"]
        out_name = "audit_march7.txt"
    elif selector.startswith("ids:"):
        ids = set(selector[4:].split(","))
        selected = [i for i in incs if i["incident_id"] in ids]
        out_name = "audit_sample.txt"
    else:
        print("unknown selector")
        return

    out_path = PROCESSED_DIR / out_name
    with out_path.open("w", encoding="utf-8") as f:
        for inc in selected:
            f.write("=" * 100 + "\n")
            f.write(f"{inc['incident_id']} | {inc['town']} | {inc['event_date']} | "
                     f"deaths_final={inc['deaths_final']} injuries_final={inc['injuries_final']} | "
                     f"district={inc['district']} governorate={inc['governorate']} | "
                     f"attack_type={inc['attack_type']}\n")
            f.write(f"location_ambiguous={inc['location_ambiguous']} casualty_count_ambiguous={inc['casualty_count_ambiguous']}\n")
            f.write(f"merge_notes: {inc['merge_notes']}\n")
            f.write("-" * 100 + "\n")
            for u in upd_by_incident.get(inc["incident_id"], []):
                base_id = u["article_id"].rstrip("abcdefghij")
                art = load_article(base_id)
                f.write(f"  [{u['article_id']}] deaths={u['deaths_reported']} injuries={u['injuries_reported']} "
                        f"({u['preliminary_or_final']}) url={u['article_url']}\n")
                if art:
                    f.write(f"    TITLE: {art['title']}\n")
                    f.write(f"    BODY: {art['body']}\n")
                f.write(f"    row_notes: {u['notes']}\n\n")
            f.write("\n")

    print(f"Wrote {out_path} ({len(selected)} incidents)")


if __name__ == "__main__":
    main()
