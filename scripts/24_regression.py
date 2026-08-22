import csv
import datetime as dt
import re
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

with open("data/processed/location_day.csv", encoding="utf-8-sig") as f:
    ld = {r["location_day_id"]: r for r in csv.DictReader(f)}
with open("data/processed/coverage_results_FINAL.csv", encoding="utf-8-sig") as f:
    cov = list(csv.DictReader(f))

ANCHOR = dt.date(2026, 3, 2)  # Monday, week 1 start


def deaths_numeric(s):
    m = re.match(r"(\d+)", s or "")
    return int(m.group(1)) if m else None


rows = []
for r in cov:
    ldrow = ld.get(r["location_day_id"])
    if not ldrow:
        continue
    d = deaths_numeric(ldrow.get("deaths_total", ""))
    if d is None:
        continue  # exclude unspecified-death rows from the regression entirely
    event_date = dt.date.fromisoformat(r["event_date"])
    week = (event_date - ANCHOR).days // 7 + 1
    gov = ldrow.get("governorate", "")
    rows.append({
        "location_day_id": r["location_day_id"],
        "status": r["status"],
        "deaths": d,
        "log1p_deaths": np.log1p(d),
        "south_or_nabatieh": 1 if gov in ("South Lebanon", "Nabatieh") else 0,
        "event_week": week,
        "governorate": gov,
    })

df = pd.DataFrame(rows)
print(f"Total rows with known numeric deaths: {len(df)}")
print(f"By status: {df['status'].value_counts().to_dict()}")


def run_model(data, label):
    d = data.copy()
    d["covered"] = (d["status"] == "covered").astype(int)
    n = len(d)
    n_covered = d["covered"].sum()
    if n_covered == 0 or n_covered == n:
        print(f"\n=== {label} === n={n}: degenerate outcome (all 0 or all 1), cannot fit")
        return
    model = smf.logit("covered ~ log1p_deaths + south_or_nabatieh + event_week", data=d).fit(disp=0)
    print(f"\n=== {label} === n={n}, covered={n_covered}")
    print(model.summary2().tables[1])
    conf = model.conf_int()
    or_table = pd.DataFrame({
        "OR": np.exp(model.params),
        "CI_low": np.exp(conf[0]),
        "CI_high": np.exp(conf[1]),
        "p": model.pvalues,
    })
    print(or_table)
    return model, or_table


with open("scripts/24_regression_output.txt", "w", encoding="utf-8") as out:
    import contextlib
    with contextlib.redirect_stdout(out):
        print(f"Total rows with known numeric deaths: {len(df)}")
        print(f"By status: {df['status'].value_counts().to_dict()}")

        # Primary: resolved only (covered vs uncovered)
        resolved = df[df["status"].isin(["covered", "uncovered"])]
        run_model(resolved, "PRIMARY: resolved cases only (covered vs uncovered)")

        # Sensitivity 1: unresolved treated as covered
        sens_covered = df.copy()
        sens_covered.loc[sens_covered["status"] == "unresolved", "status"] = "covered"
        run_model(sens_covered, "SENSITIVITY: unresolved treated as covered")

        # Sensitivity 2: unresolved treated as uncovered
        sens_uncovered = df.copy()
        sens_uncovered.loc[sens_uncovered["status"] == "unresolved", "status"] = "uncovered"
        run_model(sens_uncovered, "SENSITIVITY: unresolved treated as uncovered")

print("done, see scripts/24_regression_output.txt")
