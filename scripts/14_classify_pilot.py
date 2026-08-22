"""
Pilot classification pass: for each location-day's raw returned stories,
mark title_confirmed relevance (alias/synonym literally in the title) vs
unconfirmed (Media Cloud matched somewhere in full text, not verifiable from
title alone -- story_list does not return snippets or body text).

Also flags likely Lebanese-domestic outlets (using media_source_universe /
Lebanon-National collection reference list is not source-level here, so we
use a simple TLD/domain heuristic list built from the .lb ccTLD and known
Lebanese outlets seen in the raw data) and likely wire-service origin
(byline/outlet-name match against AP/Reuters/AFP/Anadolu/Xinhua).
"""
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = PROCESSED_DIR / "media_search_raw"
OUT_DIR = PROCESSED_DIR / "media_classified"
OUT_DIR.mkdir(exist_ok=True)

WIRE_MARKERS = ["aa.com.tr", "apnews.com", "reuters.com", "afp.com", "xinhuanet.com", "xinhua"]
LEBANESE_DOMAIN_MARKERS = [".lb", "almanar.com.lb", "naharnet.com", "nna-leb.gov.lb", "lbcgroup.tv", "mtv.com.lb", "aljadeed.tv", "elnashra.com", "annahar.com"]


def load_aliases():
    with (PROCESSED_DIR / "location_aliases.csv").open(encoding="utf-8-sig") as f:
        return {r["location"]: r for r in csv.DictReader(f)}


def load_location_days():
    with (PROCESSED_DIR / "location_day.csv").open(encoding="utf-8-sig") as f:
        return {r["location_day_id"]: r for r in csv.DictReader(f)}


def load_log():
    with (PROCESSED_DIR / "media_search_log.csv").open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def is_wire(media_name, url):
    s = (media_name + " " + url).lower()
    return any(m in s for m in WIRE_MARKERS)


def is_lebanese_domain(media_name):
    s = media_name.lower()
    return any(m in s for m in LEBANESE_DOMAIN_MARKERS)


def title_matches(title, alias_terms):
    t = title.lower()
    for a in alias_terms:
        a = a.strip().lower()
        if not a:
            continue
        if a in t:
            return True
    return False


def main():
    aliases = load_aliases()
    ld = load_location_days()
    log_rows = load_log()

    summary_rows = []

    for lr in log_rows:
        ldid = lr["location_day_id"]
        loc = lr["location"]
        alias_terms = lr["aliases_used"].split(";")
        raw_path = BASE_DIR / lr["raw_results_file"]
        if not raw_path.exists():
            continue
        with raw_path.open(encoding="utf-8-sig") as f:
            stories = list(csv.DictReader(f))

        classified = []
        for s in stories:
            title = s.get("title", "")
            media_name = s.get("media_name", "")
            url = s.get("url", "")
            matched = title_matches(title, alias_terms)
            leb = is_lebanese_domain(media_name)
            wire = is_wire(media_name, url)
            classified.append({
                **s,
                "title_confirmed_relevant": "1" if matched else "0",
                "is_lebanese_domain": "1" if leb else "0",
                "is_wire_service": "1" if wire else "0",
            })

        out_path = OUT_DIR / f"{ldid.replace('/', '_')}.csv"
        fieldnames = ["title", "media_name", "media_url", "url", "publish_date", "language",
                      "indexed_date", "title_confirmed_relevant", "is_lebanese_domain", "is_wire_service"]
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for c in classified:
                w.writerow({k: c.get(k, "") for k in fieldnames})

        confirmed = [c for c in classified if c["title_confirmed_relevant"] == "1"]
        confirmed_non_leb = [c for c in confirmed if c["is_lebanese_domain"] == "0"]
        all_non_leb = [c for c in classified if c["is_lebanese_domain"] == "0"]
        confirmed_domains = sorted(set(c["media_name"] for c in confirmed_non_leb))
        all_domains_upper_bound = sorted(set(c["media_name"] for c in all_non_leb))
        wire_hits = sorted(set(c["media_name"] for c in classified if c["is_wire_service"] == "1"))

        ldrow = ld.get(ldid, {})
        summary_rows.append({
            "location_day_id": ldid,
            "location": loc,
            "event_date": lr["event_date"],
            "deaths_total": ldrow.get("deaths_total", ""),
            "injuries_total": ldrow.get("injuries_total", ""),
            "governorate": ldrow.get("governorate", ""),
            "is_ambiguous_common_word": lr["is_ambiguous"],
            "result_count_3d": lr["result_count_3d"],
            "result_count_7d": lr["result_count_7d"],
            "stories_returned_3d": lr["stories_returned_3d"],
            "title_confirmed_articles": len(confirmed),
            "title_confirmed_non_lebanese_articles": len(confirmed_non_leb),
            "primary_outcome_confirmed_unique_non_lebanese_domains": len(confirmed_domains),
            "confirmed_domains_list": ";".join(confirmed_domains),
            "upper_bound_unique_non_lebanese_domains_all_returned": len(all_domains_upper_bound),
            "any_coverage_title_confirmed": "1" if confirmed_non_leb else "0",
            "any_coverage_any_returned": "1" if all_non_leb else "0",
            "seven_day_result_count": lr["result_count_7d"],
            "seven_day_gt_three_day": "1" if (lr["result_count_7d"] not in ("", None) and lr["result_count_3d"] not in ("", None) and int(lr["result_count_7d"] or 0) > int(lr["result_count_3d"] or 0)) else "0",
            "wire_service_domains_seen": ";".join(wire_hits),
        })

    out_summary = PROCESSED_DIR / "pilot_classification_summary.csv"
    with out_summary.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    with (BASE_DIR / "scripts" / "14_classify_pilot.progress.log").open("w", encoding="utf-8") as f:
        f.write(f"Classified {len(summary_rows)} location-days. Wrote {out_summary}\n")
        for r in summary_rows:
            f.write(f"{r['location_day_id'].encode('ascii','backslashreplace').decode('ascii')} | "
                    f"confirmed={r['title_confirmed_articles']} | "
                    f"confirmed_domains={r['primary_outcome_confirmed_unique_non_lebanese_domains']} | "
                    f"upper_bound_domains={r['upper_bound_unique_non_lebanese_domains_all_returned']} | "
                    f"any_coverage_confirmed={r['any_coverage_title_confirmed']}\n")


if __name__ == "__main__":
    main()
