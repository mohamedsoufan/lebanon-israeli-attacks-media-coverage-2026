"""
Stage 1, steps 6-8: merge reports about the same attack into one incident row,
preserving individual reports in an updates table. Handles multi-location
reports (already pre-split into sub-rows like "417806b" during classification
when deaths were separable by location).

Merge key: (canonical location, event_date). Within a group, articles are
sorted chronologically; the latest non-blank deaths/injuries figure is used
as the incident's current best estimate ("use the latest credible casualty
count"), and every individual report is preserved in incidents_updates.csv.

A small manual alias list handles known cross-spelling duplicates
(e.g. Qalawiyeh spelled two ways for the same March 6 strike) identified
during classification.
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# manual merge overrides: (town_field, event_date) -> canonical (town_field, event_date)
# used only for the specific cross-spelling/duplicate-report cases flagged in notes
MANUAL_ALIASES = {
    ("قلويه (Qalawiyeh)", "2026-03-06"): ("قلاويه (Qalawiyeh)", "2026-03-06"),
    # Nabi Chit commando raid: Army corroboration statement uses a different town label
    ("النبي شيت / الخريبة", "2026-03-07"):
        ("النبي شيت (Nabi Chit - raid also affected Khirbeh/Sarain/Ali al-Nahri)", "2026-03-07"),
    # cross-midnight: strike reported at night, confirmed the following calendar day
    ("جبال البطم (Jabal al-Botm)", "2026-03-08"): ("جبال البطم (Jabal al-Botm)", "2026-03-07"),
    ("جويا (Joya)", "2026-03-08"): ("جويا (Joya)", "2026-03-09"),
    ("الرملة البيضاء (Ramlet al-Baida)", "2026-03-12"): ("الرملة البيضاء (Ramlet al-Baida)", "2026-03-11"),
    ("النبطية (Nabatieh city - Al-Rahibat neighborhood)", "2026-03-14"):
        ("النبطية (Nabatieh city - Al-Rahibat neighborhood)", "2026-03-13"),
    ("بعلبك (Baalbek city - Ras al-Ain)", "2026-03-18"): ("بعلبك (Baalbek city - Ras al-Ain)", "2026-03-17"),
    # same March 18 Beirut dawn strikes, reported under three different location labels
    ("زقاق البلاط (Zuqaq al-Blat)", "2026-03-18"): ("بيروت (Beirut - two strikes)", "2026-03-18"),
    ("البسطة / زقاق البلاط (Basta / Zuqaq al-Blat)", "2026-03-18"): ("بيروت (Beirut - two strikes)", "2026-03-18"),
    # same strike, town label narrowed in the update
    ("شعت (Chaat - toward Younine)", "2026-03-18"): ("شعت (Chaat)", "2026-03-18"),
    # same strike, two different location labels for the Sidon coastal road/Corniche
    ("صيدا (Sidon coastal road)", "2026-03-18"): ("صيدا (Sidon Corniche)", "2026-03-18"),
    # same strike (journalists killed), vague first report vs named follow-up
    ("Jezzine-Kfarhouneh road", "2026-03-28"): ("طريق جزين (Jezzine road)", "2026-03-28"),
    # same car strike, "Khaldeh" vs "Khaldeh highway" labels
    ("خلدة (Khaldeh highway)", "2026-03-31"): ("خلدة (Khaldeh)", "2026-03-31"),
}

# validation-audit fix: these article_ids were classified with the same town+date
# as another report and so auto-merged, but re-reading the source text shows they
# describe a DIFFERENT, non-overlapping attack (different target/time same day) -
# force them into their own incident group instead of merging.
FORCE_SPLIT_KEY = {
    # Jbeshit: 418093 is the dawn single-home massacre (6 dead, named family);
    # 418222b is a separate "afternoon escalation" strike on the town generally (3 dead)
    "418222b": ("جبشيت (Jbeshit - separate afternoon strike)", "2026-03-07"),
    # Kawthariyet al-Rez: 418139 hit the sheikh's home (2 dead, his sons);
    # 418252 is a distinct strike specifically on a civil-defense/health responder team (3 dead)
    "418252": ("كوثرية الرز (Kawthariyet al-Rez - separate responder-team strike)", "2026-03-07"),
    # Sohmor: 420899/420936 describe one strike (4 homes, revised 4->2 dead);
    # 420959 is described as "a strike moments ago" hitting a further, single home (2 dead)
    "420959": ("سحمر (Sohmor - separate later strike)", "2026-03-18"),
    # Kfarra: 423950b is a brief generic "2 dead" afternoon-strike mention;
    # 423953 is a distinct, specifically-targeted strike on a responder gathering point (1 dead)
    "423953": ("كفرا (Kfarra - separate responder-point strike)", "2026-03-31"),
    # Nmeiriyeh: after correcting 418874/418963's event_date (Mar 10 -> Mar 9, per
    # explicit "last night" text - see event-date validation audit), they now share
    # a date with 418802's unrelated-looking 7-dead report. Kept separate since 418802
    # names no victims while 418874/418963 name the Hamdan family specifically - possibly
    # the same strike reported two ways, but not confirmed, so not force-merged either.
    "418874": ("النميرية (Al-Nmeiriyeh - Hamdan family strike)", "2026-03-09"),
    "418963": ("النميرية (Al-Nmeiriyeh - Hamdan family strike)", "2026-03-09"),
}

# validation-audit fix: MoPH/NNA "grand total across an entire town cluster" bulletins
# that explicitly overlap other, separately-tracked incidents (double-counting risk if
# left in the incident-level sum). Routed to grand_totals_excluded.csv instead of
# incidents.csv; kept out of any incident-level or location-day total.
GRAND_TOTAL_ARTICLE_IDS = {
    # "Total for Nabi Chit and surrounding towns: 41 dead" - explicitly does not equal
    # the sum of the separately-tracked residential chain (16) + commando raid (26) +
    # Shamsatar (6) = 48. See VALIDATION_REPORT.md section 3.
    "418161",
}

# validation-audit fix: for these incidents, the chronologically LATEST report is
# not actually the most complete one (e.g. a later field mention names only some
# victims while an earlier MoPH bulletin gives the fuller aggregate count) - override
# deaths_final to the more complete/credible figure per manual review of the source text.
DEATHS_FINAL_OVERRIDE = {
    # Tibnine Mar 11: MoPH's 8 (16:53) is the fuller aggregate count; the later field
    # report (17:28) only names 5 of those 8 victims specifically, it isn't a revision down
    ("تبنين (Tibnine)", "2026-03-11"): "8",
}


def load_articles():
    with (PROCESSED_DIR / "articles.csv").open(encoding="utf-8-sig") as f:
        return {r["article_id"]: r for r in csv.DictReader(f)}


def base_article_id(article_id: str) -> str:
    # strip trailing letter suffix used for split multi-location sub-rows (e.g. "417806b" -> "417806")
    return article_id.rstrip("abcdefghij") if not article_id.isdigit() else article_id


def main():
    articles = load_articles()
    with (PROCESSED_DIR / "candidates_classified.csv").open(encoding="utf-8-sig") as f:
        all_included = [r for r in csv.DictReader(f) if r["include"] == "1"]

    grand_total_rows = [r for r in all_included if r["article_id"] in GRAND_TOTAL_ARTICLE_IDS]
    rows = [r for r in all_included if r["article_id"] not in GRAND_TOTAL_ARTICLE_IDS]

    print(f"{len(rows)} included reports to merge ({len(grand_total_rows)} grand-total bulletins routed to audit table)")

    # attach lookup info (url, lastmod) via base article id
    for r in rows:
        base = base_article_id(r["article_id"])
        art = articles.get(base)
        if art is None:
            print(f"  WARN: no article lookup for {r['article_id']} (base {base})")
            r["_url"] = ""
            r["_lastmod"] = r["article_id"]  # fallback sort key
        else:
            r["_url"] = art["article_url"]
            r["_lastmod"] = art["lastmod"]

    # build merge key with manual alias resolution
    groups = {}
    for r in rows:
        if r["article_id"] in FORCE_SPLIT_KEY:
            key = FORCE_SPLIT_KEY[r["article_id"]]
        else:
            key = (r["town"], r["event_date"])
            key = MANUAL_ALIASES.get(key, key)
        groups.setdefault(key, []).append(r)

    print(f"{len(groups)} incident groups")

    incidents = []
    updates = []
    incident_num = 0

    for (town, event_date), group in sorted(groups.items(), key=lambda kv: (kv[0][1] or "", kv[0][0] or "")):
        incident_num += 1
        incident_id = f"INC-{incident_num:04d}"
        group_sorted = sorted(group, key=lambda r: r["_lastmod"])

        def latest_nonblank(field):
            for r in reversed(group_sorted):
                v = (r.get(field) or "").strip()
                if v:
                    return v
            return ""

        deaths_final = DEATHS_FINAL_OVERRIDE.get((town, event_date), latest_nonblank("deaths_reported"))
        injuries_final = latest_nonblank("injuries_reported")
        district = latest_nonblank("district")
        governorate = latest_nonblank("governorate")
        attack_type = latest_nonblank("attack_type")
        target_description = latest_nonblank("target_description")
        location_raw = latest_nonblank("location_raw")

        location_ambiguous = "1" if any(r["location_ambiguous"] == "1" for r in group_sorted) else "0"
        casualty_count_ambiguous = "1" if any(r["casualty_count_ambiguous"] == "1" for r in group_sorted) else "0"

        first_report = group_sorted[0]
        final_report = group_sorted[-1]

        all_urls = ";".join(r["_url"] for r in group_sorted if r["_url"])
        all_article_ids = ";".join(r["article_id"] for r in group_sorted)
        merge_notes = " | ".join(r["notes"] for r in group_sorted if r.get("notes"))

        incidents.append({
            "incident_id": incident_id,
            "event_date": event_date,
            "town": town,
            "location_raw": location_raw,
            "district": district,
            "governorate": governorate,
            "deaths_final": deaths_final,
            "injuries_final": injuries_final,
            "attack_type": attack_type,
            "target_description": target_description,
            "first_nna_report": first_report["_lastmod"],
            "final_nna_update": final_report["_lastmod"],
            "nna_url_count": str(len(group_sorted)),
            "all_nna_urls": all_urls,
            "all_article_ids": all_article_ids,
            "location_ambiguous": location_ambiguous,
            "casualty_count_ambiguous": casualty_count_ambiguous,
            "merge_notes": merge_notes,
        })

        for r in group_sorted:
            updates.append({
                "incident_id": incident_id,
                "article_id": r["article_id"],
                "article_url": r["_url"],
                "lastmod": r["_lastmod"],
                "deaths_reported": r["deaths_reported"],
                "injuries_reported": r["injuries_reported"],
                "preliminary_or_final": r["preliminary_or_final"],
                "notes": r["notes"],
            })

    inc_path = PROCESSED_DIR / "incidents.csv"
    with inc_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(incidents[0].keys()))
        w.writeheader()
        w.writerows(incidents)
    print(f"Wrote {inc_path} ({len(incidents)} incidents)")

    upd_path = PROCESSED_DIR / "incident_updates.csv"
    with upd_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(updates[0].keys()))
        w.writeheader()
        w.writerows(updates)
    print(f"Wrote {upd_path} ({len(updates)} update rows)")

    # grand-total bulletins: audit-only, excluded from incidents.csv and any death sum
    gt_out = []
    for r in grand_total_rows:
        base = base_article_id(r["article_id"])
        art = articles.get(base, {})
        gt_out.append({
            "article_id": r["article_id"],
            "event_date": r["event_date"],
            "town_or_scope": r["town"],
            "deaths_reported": r["deaths_reported"],
            "injuries_reported": r["injuries_reported"],
            "article_url": art.get("article_url", ""),
            "lastmod": art.get("lastmod", ""),
            "reason_excluded": r["notes"],
        })
    gt_path = PROCESSED_DIR / "grand_totals_excluded.csv"
    with gt_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(gt_out[0].keys()))
        w.writeheader()
        w.writerows(gt_out)
    print(f"Wrote {gt_path} ({len(gt_out)} grand-total bulletins, audit-only, excluded from incident totals)")


if __name__ == "__main__":
    main()
