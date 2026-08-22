"""
Validation-audit deliverable: a location-day aggregate view, built alongside
(not replacing) incidents.csv.

Rationale: same-town, same-day attacks can usually be told apart from NNA's
own text (named victims, explicit target descriptions, "second/renewed
strike" language, distinct MoPH toll structures) - see the validation
report for how reliable that judgment call is. But for the ~10-15% of
cases where the source text itself doesn't disambiguate, incident-level
counts embed a judgment call. This file sidesteps that by summing
everything reported for the same place on the same calendar day, regardless
of whether it was one strike or several - a coarser, more conservative unit
for anyone who wants to cross-check the incident-level numbers.
"""
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# strips ANY parenthetical sub-qualifier after " - " (whether an incident-level
# disambiguation like "separate afternoon strike", a named-victim tag like
# "Hamdan family strike", or a specific neighborhood like "Ras al-Ain") down to
# just the base place name, e.g. "جبشيت (Jbeshit - separate afternoon strike)"
# -> "جبشيت (Jbeshit)". This is deliberately coarser than the incident-level town
# field: for Media Cloud search purposes a neighborhood-level or attack-level
# distinction is usually invisible to international coverage anyway, so this
# view collapses all of it down to "what place would a search term for this day
# actually name".
PAREN_RE = re.compile(r"\(([^)]*)\)")


def normalize_town(town: str) -> str:
    if not town:
        return town
    m = PAREN_RE.search(town)
    if not m:
        return town.strip()
    inner = m.group(1)
    base = inner.split(" - ")[0].strip()
    prefix = town[: m.start()].strip()
    return f"{prefix} ({base})" if prefix else f"({base})"


def main():
    with (PROCESSED_DIR / "incidents.csv").open(encoding="utf-8-sig") as f:
        incs = list(csv.DictReader(f))

    groups = {}
    for i in incs:
        key = (normalize_town(i["town"]), i["event_date"])
        groups.setdefault(key, []).append(i)

    rows = []
    for (town, date), members in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        deaths = sum(int(m["deaths_final"]) for m in members if m["deaths_final"].isdigit())
        injuries = sum(int(m["injuries_final"]) for m in members if m["injuries_final"].isdigit())
        has_unquantified = any(not m["deaths_final"].isdigit() for m in members)
        if has_unquantified:
            deaths_display = f"{deaths}+ (unspecified additional reported)" if deaths > 0 else "unknown (unspecified, >=1 per NNA)"
        else:
            deaths_display = str(deaths)
        districts = sorted(set(m["district"] for m in members if m["district"]))
        governorates = sorted(set(m["governorate"] for m in members if m["governorate"]))
        all_incident_ids = ";".join(m["incident_id"] for m in members)
        rows.append({
            "location_day_id": f"LD-{date}-{town}"[:80],
            "event_date": date,
            "location": town,
            "district": ";".join(districts),
            "governorate": ";".join(governorates),
            "deaths_total": deaths_display,
            "injuries_total": injuries,
            "incident_rows_combined": len(members),
            "has_unquantified_report": "1" if has_unquantified else "0",
            "component_incident_ids": all_incident_ids,
        })

    out_path = PROCESSED_DIR / "location_day.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} location-day rows, from {len(incs)} incident rows)")

    multi = [r for r in rows if r["incident_rows_combined"] > 1]
    print(f"{len(multi)} location-day rows combine more than one incidents.csv row")


if __name__ == "__main__":
    main()
