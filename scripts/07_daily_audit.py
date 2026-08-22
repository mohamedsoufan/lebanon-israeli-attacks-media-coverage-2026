"""
Stage 1, step 9: for each day, sum NNA-incident deaths and compare against
the change in MoPH's cumulative total. Also pulls the daily cumulative
figures MoPH itself gave to NNA (from the "general daily bulletin" articles
we excluded from the incident set) as an interim cross-check while the
user's official MoPH EOC PDF bulletins are pending.
"""
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# matches "منذ 2 آذار حتى <day> <month>" cumulative bulletins and pulls the
# cumulative death figure + the report's own date from lastmod
CUM_RE = re.compile(r"(\d{1,4})\s*شهيد")


def daily_incident_sums():
    with (PROCESSED_DIR / "incidents.csv").open(encoding="utf-8-sig") as f:
        incs = list(csv.DictReader(f))
    sums = {}
    for i in incs:
        d = i["event_date"]
        if not d:
            continue
        val = i["deaths_final"]
        n = int(val) if val.isdigit() else 0
        sums.setdefault(d, {"deaths": 0, "incidents": 0, "unquantified": 0})
        sums[d]["deaths"] += n
        sums[d]["incidents"] += 1
        if not val.isdigit():
            sums[d]["unquantified"] += 1
    return sums


def moph_cumulative_bulletins():
    with (PROCESSED_DIR / "candidates_classified.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with (PROCESSED_DIR / "articles.csv").open(encoding="utf-8-sig") as f:
        articles = {r["article_id"]: r for r in csv.DictReader(f)}

    bulletins = {}
    for r in rows:
        if r["include"] != "0":
            continue
        if "cumulative" not in (r["exclusion_reason"] or "").lower():
            continue
        art = articles.get(r["article_id"])
        if not art:
            continue
        date = art["lastmod"][:10]
        m = CUM_RE.search(art["title"] + " " + art["body"])
        if not m:
            continue
        cum_val = int(m.group(1))
        # keep the latest bulletin per calendar day
        if date not in bulletins or art["lastmod"] > bulletins[date][1]:
            bulletins[date] = (cum_val, art["lastmod"])
    return {d: v[0] for d, v in bulletins.items()}


def main():
    inc_sums = daily_incident_sums()
    moph_cum = moph_cumulative_bulletins()

    dates = sorted(set(inc_sums) | set(moph_cum))
    prev_cum = None
    rows_out = []
    for d in dates:
        nna_deaths = inc_sums.get(d, {}).get("deaths", 0)
        n_incidents = inc_sums.get(d, {}).get("incidents", 0)
        unquant = inc_sums.get(d, {}).get("unquantified", 0)
        cum = moph_cum.get(d)
        moph_daily_change = (cum - prev_cum) if (cum is not None and prev_cum is not None) else ""
        if cum is not None:
            prev_cum = cum
        rows_out.append({
            "date": d,
            "nna_incident_deaths": nna_deaths,
            "nna_incident_count": n_incidents,
            "nna_incidents_with_unquantified_deaths": unquant,
            "moph_cumulative_total_asof": cum if cum is not None else "",
            "moph_implied_daily_change": moph_daily_change,
            "difference_(nna_minus_moph_daily)": (nna_deaths - moph_daily_change) if isinstance(moph_daily_change, int) else "",
        })

    out_path = PROCESSED_DIR / "daily_audit.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote {out_path} ({len(rows_out)} days)")
    print(f"MoPH cumulative bulletins found for {len(moph_cum)} days")


if __name__ == "__main__":
    main()
