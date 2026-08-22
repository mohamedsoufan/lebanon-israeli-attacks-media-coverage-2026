"""
Stage 2 full run (post-pilot): apply the pilot-validated covered/uncovered/unresolved
method to all remaining location-days, automated to scale.

Method (mirrors the manually-verified pilot exactly):
  1. Query D0-D3 (base alias query; generic-name locations use a hard-coded
     incident-specific query instead of the bare alias, same as the pilot).
  2. Zero results -> uncovered. Record D+7 count as a secondary indicator only.
  3. Non-zero -> inspect results in returned order, skipping Lebanese-domain
     candidates outright (they cannot count as international confirmations).
     Fetch full text of each non-Lebanese candidate (requests+bs4) and check
     for an explicit match: an alias term, OR a casualty figure from the
     incident record, OR (attack_type keyword AND district/neighborhood term).
     Stop at first confirmed match. Inspect at most 10 non-Lebanese candidates
     per query stage.
  4. If none of the up-to-10 confirm, run ONE stricter fallback query built
     from the incident's target_description/attack_type/district, repeat step 3.
  5. Still nothing -> unresolved (never forced to uncovered when results existed).
  6. Fetch failures are tracked separately from content-checked non-matches.

Writes to media_search_log_full.csv (query log, one row per query attempt) and
pilot_v2_results_full.csv (one row per location-day, appended incrementally so a
crash mid-run loses nothing already decided).
"""
import csv
import datetime as dt
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
load_dotenv(BASE_DIR / ".env")
API_KEY = os.environ["MEDIACLOUD_API_KEY"]
COLLECTION_ID = 9272347

RESULTS_PATH = PROCESSED_DIR / "pilot_v2_results_full.csv"
LOG_PATH = PROCESSED_DIR / "media_search_log_full.csv"
PROGRESS_LOG = BASE_DIR / "scripts" / "19_full_run_search.progress.log"

RESULT_FIELDS = ["location_day_id", "location", "event_date", "status", "confirming_url",
                  "confirmation_method", "query_used", "reason"]
LOG_FIELDS = ["location_day_id", "stage", "query", "result_count_3d", "result_count_7d", "timestamp"]

LEBANESE_DOMAIN_MARKERS = [
    ".lb", "almanar.com.lb", "naharnet.com", "nna-leb.gov.lb", "lbcgroup.tv",
    "mtv.com.lb", "aljadeed.tv", "elnashra.com", "annahar.com", "dailystar.com.lb",
    "ya-libnan.com", "lbci.tv", "aljoumhouria.com",
]

STOPWORDS = {"unspecified", "the", "a", "an", "of", "and", "on", "in", "for", "to", "with", "residential", "building"}

# Generic-name location-days: bare major-city/district-capital alias would be too
# broad (same problem found for Beirut/Tyre/Zahle-Kark in the pilot). Hard-coded
# incident-specific queries, built the same way as the pilot's 3 generic cases.
GENERIC_QUERIES = {
    "LD-2026-03-04-بعلبك (Baalbek city)": '("Baalbek" OR "Baalbeck") AND Lebanon AND (residential OR "6 killed" OR building OR airstrike)',
    "LD-2026-03-17-بعلبك (Baalbek city)": '("Baalbek" OR "Baalbeck") AND Lebanon AND ("Ras al-Ain" OR "4 killed" OR residential)',
    "LD-2026-03-06-صيدا (Sidon)": '("Sidon" OR "Saida") AND Lebanon AND ("Al-Maqassed" OR "5 killed")',
    "LD-2026-03-18-صيدا (Sidon Corniche)": '("Sidon" OR "Saida") AND Lebanon AND (corniche OR vehicle OR "Civil Defense" OR "civil defence")',
    "LD-2026-03-11-النبطية (Nabatieh city)": '("Nabatieh" OR "Nabatiyeh") AND Lebanon AND (drone OR "1 killed")',
    "LD-2026-03-13-النبطية (Nabatieh city)": '("Nabatieh" OR "Nabatiyeh") AND Lebanon AND ("Al-Rahibat" OR "7 killed")',
    "LD-2026-03-24-النبطية (Nabatieh city)": '("Nabatieh" OR "Nabatiyeh") AND Lebanon AND ("northern entrance" OR "medics" OR "ambulance" OR motorcycle)',
    "LD-2026-03-17-Zebdine-Nabatieh road": '("Zebdine" OR "Zebdin" OR "Zibdine") AND Lebanon AND (motorcycle OR soldiers OR drone)',
    "LD-2026-03-24-Habbouch-Nabatieh highway": '("Habbouch" OR "Habboush") AND Lebanon AND (motorcycle OR drone)',
    "LD-2026-03-24-Jbeshit-Nabatieh highway": '("Jbeshit" OR "Jbaachit") AND Lebanon AND (motorcycle OR drone)',
    "LD-2026-03-27-Kfartebnit-Arnoun-Nabatieh roundabout": '("Kfartebnit" OR "Kfar Tebnit" OR "Arnoun" OR "Arnoune") AND Lebanon AND ("Islamic Health" OR medics OR responder)',
}


def progress(msg):
    with PROGRESS_LOG.open("a", encoding="utf-8") as f:
        f.write(msg.encode("ascii", "backslashreplace").decode("ascii") + "\n")


def is_lebanese_domain(media_name):
    s = (media_name or "").lower()
    return any(m in s for m in LEBANESE_DOMAIN_MARKERS)


def load_aliases():
    with (PROCESSED_DIR / "location_aliases.csv").open(encoding="utf-8-sig") as f:
        return {r["location"]: r for r in csv.DictReader(f)}


def load_location_days():
    with (PROCESSED_DIR / "location_day.csv").open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_incidents():
    with (PROCESSED_DIR / "incidents.csv").open(encoding="utf-8-sig") as f:
        return {r["incident_id"]: r for r in csv.DictReader(f)}


def load_pilot_ids():
    with (PROCESSED_DIR / "pilot_v2_results.csv").open(encoding="utf-8-sig") as f:
        return {r["location_day_id"] for r in csv.DictReader(f)}


def already_done_ids():
    if not RESULTS_PATH.exists():
        return set()
    with RESULTS_PATH.open(encoding="utf-8-sig") as f:
        return {r["location_day_id"] for r in csv.DictReader(f)}


def build_base_query(loc_row):
    aliases = loc_row["aliases"].split(";")
    alias_clause = " OR ".join(f'"{a.strip()}"' for a in aliases if a.strip())
    q = f"({alias_clause}) AND Lebanon"
    if loc_row["is_ambiguous_common_word"] == "1":
        q += " AND (strike OR airstrike OR raid OR killed OR attack OR shelling)"
    return q


def build_fallback_query(loc_row, ld_row, incidents):
    comp_ids = [i.strip() for i in ld_row["component_incident_ids"].split(";") if i.strip()]
    terms = set()
    for iid in comp_ids:
        inc = incidents.get(iid)
        if not inc:
            continue
        for field in ("target_description", "attack_type"):
            val = inc.get(field, "")
            for word in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", val):
                if word.lower() not in STOPWORDS:
                    terms.add(word)
    aliases = loc_row["aliases"].split(";")
    alias_clause = " OR ".join(f'"{a.strip()}"' for a in aliases if a.strip())
    if terms:
        term_clause = " OR ".join(f'"{t}"' for t in list(terms)[:6])
        return f'({alias_clause}) AND Lebanon AND ({term_clause})'
    return f'({alias_clause}) AND Lebanon AND (strike OR airstrike OR raid OR killed OR attack OR shelling)'


SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
_adapter = requests.adapters.HTTPAdapter(max_retries=0, pool_connections=20, pool_maxsize=20)
SESSION.mount("http://", _adapter)
SESSION.mount("https://", _adapter)


def fetch_text(url, timeout=(3, 5)):
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:20000]


def check_terms(t, loc_row, ld_row, incidents):
    """t is already-lowercased text (title or full body)."""
    for a in loc_row["aliases"].split(";"):
        a = a.strip().lower()
        if a and len(a) > 3 and a in t:
            return True, f'alias match: "{a}"'
    deaths = ld_row["deaths_total"]
    m = re.match(r"(\d+)", deaths)
    if m:
        n = m.group(1)
        # numeric word-boundary match: "\b2 killed\b" must not match inside "12 killed" or "2,000 killed"
        for phrase in (rf"\b{n} killed\b", rf"\b{n} dead\b", rf"\b{n} people were killed\b", rf"\bkilled {n}\b"):
            if re.search(phrase, t):
                return True, f'casualty match: "{phrase}"'
    comp_ids = [i.strip() for i in ld_row["component_incident_ids"].split(";") if i.strip()]
    for iid in comp_ids:
        inc = incidents.get(iid)
        if not inc:
            continue
        target = (inc.get("target_description") or "").lower()
        for word in re.findall(r"[a-z][a-z\-]{4,}", target):
            if word not in STOPWORDS and word in t:
                return True, f'target-description match: "{word}"'
    return False, ""


def confirms_title(title, loc_row, ld_row, incidents):
    return check_terms((title or "").lower(), loc_row, ld_row, incidents)


def confirms(text, loc_row, ld_row, incidents):
    return check_terms(text.lower(), loc_row, ld_row, incidents)


def with_retry(fn, ldid, stage, label, max_attempts=7):
    delay = 3.0
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            is_rate_limit = "429" in str(e) or "rate limited" in str(e).lower()
            if is_rate_limit and attempt < max_attempts - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            progress(f"  API error ({label}) for {ldid} [{stage}] attempt {attempt+1}: {e}")
            return None
    return None


def search_and_confirm(search, ldid, loc, ld_row, aliases, incidents, query, log_rows, stage):
    start = dt.date.fromisoformat(ld_row["event_date"])
    end3 = start + dt.timedelta(days=3)
    end7 = start + dt.timedelta(days=7)

    # Single story_list call determines zero-vs-nonzero (empty page == zero results),
    # avoiding a separate story_count call for the common case.
    r_list = with_retry(lambda: search.story_list(query, start_date=start, end_date=end3, collection_ids=[COLLECTION_ID], page_size=10), ldid, stage, "story_list")
    if r_list is None:
        log_rows.append({"location_day_id": ldid, "stage": stage, "query": query,
                          "result_count_3d": "", "result_count_7d": "",
                          "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
        return "api_error", None, None, None
    page, _ = r_list
    count3 = len(page)

    count7 = None
    if count3 == 0:
        # only spend a second call on D+7 when D0-D3 came back empty (secondary indicator)
        time.sleep(0.3)
        r7 = with_retry(lambda: search.story_count(query, start_date=start, end_date=end7, collection_ids=[COLLECTION_ID]), ldid, stage, "count7")
        count7 = r7["relevant"] if r7 is not None else None

    log_rows.append({"location_day_id": ldid, "stage": stage, "query": query,
                      "result_count_3d": count3, "result_count_7d": count7 if count7 is not None else "",
                      "timestamp": dt.datetime.now().isoformat(timespec="seconds")})

    if count3 == 0:
        return "uncovered", None, None, count7

    checked = 0
    fetch_failures = 0
    for s in page:
        media_name = s.get("media_name", "")
        if is_lebanese_domain(media_name):
            continue
        if checked >= 10:
            break
        checked += 1
        url = s.get("url", "")

        ok, why = confirms_title(s.get("title", ""), aliases, ld_row, incidents)
        if ok:
            return "covered", url, f"title {why}", count7

        try:
            text = fetch_text(url)
        except Exception:
            fetch_failures += 1
            continue
        ok, why = confirms(text, aliases, ld_row, incidents)
        if ok:
            return "covered", url, why, count7

    if checked == 0:
        return "no_nonlebanese_candidates", None, None, count7
    return "not_confirmed", None, None, count7


WRITE_LOCK = threading.Lock()


def process_one(ld_row, aliases_map, incidents):
    ldid = ld_row["location_day_id"]
    loc = ld_row["location"]
    aliases = aliases_map.get(loc)
    if not aliases:
        return ldid, None, None

    search = mediacloud.api.SearchApi(API_KEY)
    log_rows = []
    base_query = GENERIC_QUERIES.get(ldid, build_base_query(aliases))
    stage1_status, url, why, count7 = search_and_confirm(search, ldid, loc, ld_row, aliases, incidents, base_query, log_rows, "base")

    result = None
    if stage1_status == "covered":
        result = {"status": "covered", "confirming_url": url, "confirmation_method": why, "query_used": base_query,
                  "reason": f"Confirmed via full-text fetch, base/generic query. {why}"}
    elif stage1_status == "uncovered":
        note = ""
        if count7 and count7 > 0:
            note = f" Secondary D+7 indicator: {count7} results (not confirmed to an article, informational only)."
        result = {"status": "uncovered", "confirming_url": "", "confirmation_method": "",
                  "query_used": base_query, "reason": f"Zero results at D0-D3.{note}"}
    else:
        if stage1_status == "api_error":
            result = {"status": "unresolved", "confirming_url": "", "confirmation_method": "",
                      "query_used": base_query, "reason": "API error during base query; not retried automatically."}
        else:
            fb_query = build_fallback_query(aliases, ld_row, incidents)
            stage2_status, url2, why2, count7b = search_and_confirm(search, ldid, loc, ld_row, aliases, incidents, fb_query, log_rows, "fallback")
            count7 = count7 or count7b
            if stage2_status == "covered":
                result = {"status": "covered", "confirming_url": url2, "confirmation_method": why2, "query_used": fb_query,
                          "reason": f"Base query did not confirm ({stage1_status}); fallback query confirmed. {why2}"}
            elif stage2_status == "uncovered":
                result = {"status": "uncovered", "confirming_url": "", "confirmation_method": "",
                          "query_used": fb_query, "reason": f"Base query: {stage1_status}. Fallback query: zero results."}
            else:
                result = {"status": "unresolved", "confirming_url": "", "confirmation_method": "",
                          "query_used": f"base: {base_query} | fallback: {fb_query}",
                          "reason": f"Base query: {stage1_status}. Fallback query: {stage2_status}. Results existed but none confirmed among fetchable non-Lebanese candidates (or all fetches failed)."}

    row = {"location_day_id": ldid, "location": loc, "event_date": ld_row["event_date"], **result}
    return ldid, row, log_rows


def main():
    aliases_map = load_aliases()
    location_days = load_location_days()
    incidents = load_incidents()
    pilot_ids = load_pilot_ids()
    done_ids = already_done_ids()

    remaining = [r for r in location_days if r["location_day_id"] not in pilot_ids and r["location_day_id"] not in done_ids]
    limit = os.environ.get("FULL_RUN_LIMIT")
    if limit:
        remaining = remaining[: int(limit)]
    workers = int(os.environ.get("FULL_RUN_WORKERS", "6"))
    progress(f"=== Starting full run: {len(remaining)} location-days remaining, {workers} workers ===")

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(process_one, ld_row, aliases_map, incidents): ld_row for ld_row in remaining}
        for fut in as_completed(futures):
            ld_row = futures[fut]
            ldid = ld_row["location_day_id"]
            try:
                _, row, log_rows = fut.result()
            except Exception as e:
                progress(f"WORKER ERROR for {ldid}: {e}")
                continue
            if row is None:
                progress(f"SKIP no aliases: {ldid}")
                continue

            with WRITE_LOCK:
                file_exists = RESULTS_PATH.exists()
                with RESULTS_PATH.open("a", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
                    if not file_exists:
                        w.writeheader()
                    w.writerow(row)

                file_exists = LOG_PATH.exists()
                with LOG_PATH.open("a", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                    if not file_exists:
                        w.writeheader()
                    w.writerows(log_rows)

            completed += 1
            progress(f"[{completed}/{len(remaining)}] {ldid}: {row['status']}")

    progress("=== Full run complete ===")


if __name__ == "__main__":
    main()
