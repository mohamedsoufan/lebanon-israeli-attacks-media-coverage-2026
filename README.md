# Data and code release

This directory contains everything from this study that can be publicly released: derived/structured data, the exact Media Cloud queries used, and all pipeline code. It excludes copyrighted full article text.

## What's included

**`data/` — derived, structured data (no full copyrighted article text):**
- `coverage_results_FINAL.csv` — the primary dataset: 229 fatal location-days, coverage status (covered/uncovered/unresolved), confirming URL, exact query used, and audit reasoning for every row.
- `incidents.csv`, `incident_updates.csv`, `location_day.csv`, `location_aliases.csv`, `grand_totals_excluded.csv` — Stage 1 NNA incident registry: structured fields (date, town, district, governorate, deaths, injuries, attack type) with citation-only NNA article URLs and IDs. No article body text.
- `daily_audit.csv` — the NNA-relayed casualty-total comparison (**not** an official MoPH validation — see Limitations in the paper; the true MoPH bulletin PDFs were never obtained).
- `media_source_universe.csv` — the frozen Media Cloud collection selection and rationale.
- `media_search_log.csv`, `media_search_log_full.csv` — every query run against Media Cloud: full query text, date window, collection ID, result count, API status, timestamp.
- `pilot_v2_results.csv`, `pilot_v2_results_full.csv` — per-location-day coverage decisions with reasoning (superseded by `coverage_results_FINAL.csv` but kept for the audit trail).
- `media_search_raw/`, `media_classified/` — per-location-day dumps of *returned story metadata only*: title, outlet domain, URL, publish date, language. No body text (Media Cloud's API does not return body text; nothing to strip).
- `review_batches_classified/classified_01.csv` … `classified_10.csv` — the 10 manually-classified Stage 1 batches: structured classification fields only, no article text.
- `covered_audit_sample.csv` — the fixed-seed 30-case audit sample with outcomes.

**`scripts/` — all 25 pipeline scripts**, from sitemap scraping through the final regression, unmodified.

## What's excluded, and why

- **`articles.csv`, `candidates.csv`** (Stage 1 scraped NNA article corpus — full Arabic body text of every article) — excluded. NNA holds copyright on its own wire text; we don't have distribution rights.
- **`review_batches/batch_*.txt`** (the raw article-text dumps used for manual Stage 1 classification) — excluded for the same reason.
- No international-outlet article text is included or was ever locally stored in bulk — confirming articles were fetched transiently for verification and not archived; only their titles, outlet domains, URLs, and publish dates were saved (in `media_search_raw/` and `media_classified/`), which is standard citation practice, not republication.

## Reproducing the coverage search

Given `location_day.csv`, `location_aliases.csv`, and `media_source_universe.csv`, `scripts/19_full_run_search.py` (and its pilot predecessor, `scripts/12_pilot_search.py`) will regenerate the Media Cloud queries and re-run the search exactly as documented in `media_search_log_full.csv`, modulo Media Cloud's own index changing over time (stories can be removed, corrected, or newly indexed after original publication).

## Regenerating the regression

`scripts/24_regression.py` reads `location_day.csv` and `coverage_results_FINAL.csv` directly and reproduces the logistic regression and both sensitivity analyses reported in the paper.
