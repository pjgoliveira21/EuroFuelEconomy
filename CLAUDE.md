# EuroFuelEconomy — agent context

Full project narrative, data source, and methodology: [README.md](README.md) and
[docs/METHODOLOGY.md](docs/METHODOLOGY.md). This file is operational notes for working in the
repo, not the source of truth for the analysis — if it and the docs disagree, the docs win;
update this file instead of trusting it blindly.

## Repo conventions

- `dataset/` — raw data, gitignored except the small field-description `.xlsx`. Never commit
  the CSV. Fetch it with `python scripts/00_download_data.py`.
- `db/obfcm.duckdb` — gitignored, rebuilt with `python scripts/01_build_database.py`. This is
  the boundary between the data pipeline and any application: apps/scripts downstream should
  query this file (or the small tracked `db/*.csv` result exports), never re-parse the raw CSV.
- `scripts/` — numbered pipeline steps (`00_download`, `01_build_database`,
  `02_model_country_effects`, ...). Keep new analysis steps numbered and idempotent
  (`CREATE OR REPLACE TABLE`, not `INSERT`).
- Regression uses `pyfixest`, not `statsmodels` `C(model_id)` dummies — the vehicle-family
  fixed effect has thousands of levels across millions of rows, which `pyfixest`'s demeaning
  algorithm handles; dense dummy encoding would not.

## Confirmed dataset facts (don't re-derive, just check the docs above if they seem stale)

- 7,732,320 unique vehicles, 29 countries, one row per `veh_id`, no nulls in core fields.
- Country field is `EEA_MS` → `country` in the DB. This was the step-1 blocking question in
  the original plan and is resolved.
- `RW_FC` / `gap_percentage` are JRC-precomputed real-world consumption / CO2 gap — use them to
  sanity-check the model's own `gap_log`, don't recompute real-world consumption by hand.

## Status

Phase 1 (fixed-effects country ranking) implemented and run with Portugal as reference
(`db/country_effects_ref_PT.csv`); EU-average reference also supported. Phase 2 (explaining
country effects with structural covariates) and Spritmonitor cross-validation are not started —
see README's roadmap section.
