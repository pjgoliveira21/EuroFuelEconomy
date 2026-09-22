# Methodology

## Question

Do drivers in some European countries get closer to their car's official (WLTP) fuel economy
than drivers in others, for the *same car*? The gap between real-world and official consumption
is well documented EU-wide (JRC/EEA put it around +20% on average), but that average blends
driving behavior with vehicle mix, terrain, climate, congestion, and speed limits. This project
isolates the country-level share of that gap by holding the vehicle model fixed.

## Approaches considered and rejected

- **Top-down (fuel sold ÷ vehicle fleet size).** Fuel sold = vehicle-km driven × consumption,
  and vehicle-km is unknown, so this can't isolate consumption. It's also distorted by
  heavy/bus fuel mixed into the totals and by fuel tourism (Luxembourg, the PT–ES border).
- **Manufacturer-rated range as a baseline.** Range = tank size ÷ WLTP consumption. This is a
  purely theoretical number — it carries no information about actual driving and can't be
  compared across countries.
- **Chosen approach: OBFCM real-world telemetry**, described below.

## Data

**JRC OBFCM, M1 passenger cars, 2021–2023** (CC BY 4.0). One row per unique vehicle
(`veh_id`), 7,732,320 vehicles, 29 countries. Verified properties of the raw file:

- No missing values in distance or fuel fields; each `veh_id` appears exactly once.
- Coverage is skewed toward 2023 (6.5M of 7.7M rows) as OBFCM reporting mandate ramped up —
  consistent with JRC's own note of ~27%/~19% new-registration coverage in 2021/2022. This
  means the dataset under-represents the pre-2021 fleet and, in early years, over-represents
  vehicles/brands with OTA reporting capability. Treat early-period, low-coverage countries
  with more caution.
- 4,018 distinct vehicle families (`EEA_VFN`); overlap across countries is large enough for
  fixed effects to be well identified — 11 families are observed in all 29 countries (273k
  rows), and hundreds more in 15+ countries.
- The dataset excludes battery-electric vehicles (no fuel to log) by construction — out of
  scope for this project anyway, which is about liquid-fuel driving efficiency.

Field reference: `dataset/obfcm_M1_2021_2023_table_description.xlsx` (JRC data dictionary).
Selected fields, renamed in `db/obfcm.duckdb`:

| DB column | Source field | Meaning |
|---|---|---|
| `country` | `EEA_MS` | Member State of registration |
| `vehicle_family` | `EEA_VFN` | Type-approval vehicle family — used as the "same model" unit |
| `fuel_mode` | `EEA_Fm` | M = ICEV, H = non-plug hybrid, P = plug-in hybrid |
| `fc_wltp_l_100km` | `EEA_Fc` | Official (WLTP) fuel consumption |
| `fc_real_l_100km` | `RW_FC` | Real-world fuel consumption (JRC-computed from OBFCM logs) |
| `dist_total_km` | `OBFCM_TotLifetimeDist_km` | Lifetime distance at reporting time |
| `gap_co2_pct` | `gap_percentage` | JRC's own real-vs-official CO2 gap — used as a sanity check |

## Cleaning

Applied in `vehicles_model` (built by `scripts/01_build_database.py`):

- **Exclude plug-in hybrids** (`fuel_mode = 'P'`) for this phase — their consumption depends
  on charging behavior, not driving style. ICEV and non-plug HEV are kept together, since the
  vehicle-family fixed effect already separates hybrid and non-hybrid trims of the same
  nameplate.
- **Minimum 3,000 km lifetime distance**, to exclude vehicles too new for a stable real-world
  average (drops ~457k of 7.7M rows).
- **Drop real/WLTP ratio outliers** (< 0.7 or > 2) as likely data errors (drops 5,134 of 6.3M
  eligible rows — a very small fraction, i.e. the raw data is largely clean already).

Net: 6,321,311 vehicles feed the model.

## Model

```
gap_log = ln(fc_real_l_100km / fc_wltp_l_100km)

gap_log ~ country + log(dist_total_km) | vehicle_family     [fixed effect, absorbed]
```

Estimated with `pyfixest` (high-dimensional fixed-effects OLS, absorbing `vehicle_family` by
demeaning rather than dummy-encoding 4,018 categories — necessary at this row count).
Standard errors clustered by `vehicle_family`. The country coefficient is read via
`exp(coef) - 1` as the % difference in real-world consumption vs. the reference, for the same
car. Two reference schemes are supported (`scripts/02_model_country_effects.py <ref>`):

- `PT` — every coefficient reads directly as "% more/less economical than Portugal."
- `EU` — sum-to-zero coding; every coefficient reads as "% deviation from the cross-country
  average for the same car," which is the more defensible framing for a general EU ranking.

263 singleton fixed-effect groups (vehicle families observed in only one row) are dropped
automatically — they carry no within-group variation and cannot inform the estimate.

## Validation

`gap_co2_pct` (JRC's own precomputed real-vs-WLTP CO2 gap) is available in the same dataset and
should track the model's fuel-based `gap_log` closely — used as a sanity check that the pipeline
reproduces a metric JRC has already validated, before trusting the country coefficients.

## Caveats to keep in view

- **"Driving habits" is not directly identified.** The country coefficient mixes actual driving
  style with road-type composition, congestion, speed limits, terrain, climate, and
  private-vs-company-car mix. A planned phase 2 regresses country coefficients on country-level
  covariates (mean temperature, % urban, motorway km/capita, speed limits, % company cars) to
  see how much of the gap that structurally explains — but with ~29 countries, that regression
  will have very few degrees of freedom and should be read as indicative, not conclusive.
- **OBFCM only covers cars registered 2021–2023.** It says nothing about the older fleet still
  on the road, which matters for a country like Portugal with an older-than-average car park.
- **Do not mix NEDC and WLTP** if extending this to pre-2018 data — the homologation cycles are
  not directly comparable without a conversion factor.
- **Coverage is uneven across countries and years** (see Data section) — read low-volume,
  early-period countries (e.g. Malta, Cyprus, Iceland: a few thousand rows total) with wider
  uncertainty than the confidence intervals alone suggest, since CRV1 clustering doesn't correct
  for selection into OBFCM reporting itself.

## External validation source (not yet used)

[Spritmonitor.de](https://www.spritmonitor.de) — crowdsourced consumption logs covering
pre-2021 vehicles, useful for cross-checking whether the OBFCM-era country ranking holds for
the older fleet too.
