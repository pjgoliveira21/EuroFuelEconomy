"""
Phase-1 model: gap ~ model fixed effect + country + log(distance)

gap_log = ln(real fuel consumption / WLTP fuel consumption), so a country
coefficient is (approximately, exactly via exp(coef)-1) the % more/less fuel
burned than the reference, for the SAME vehicle family (EEA_VFN), controlling
for lifetime distance. Model (EEA_VFN) is absorbed as a high-dimensional fixed
effect; standard errors are clustered by vehicle family.

Usage:
    python scripts/02_model_country_effects.py PT   # Portugal as reference
    python scripts/02_model_country_effects.py EU    # sum-to-zero (avg) reference
"""
import sys
import duckdb
import numpy as np
import pandas as pd
import pyfixest as pf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "obfcm.duckdb"

ref = sys.argv[1] if len(sys.argv) > 1 else "PT"

con = duckdb.connect(str(DB_PATH), read_only=True)
df = con.execute("""
    SELECT country, vehicle_family, gap_log, dist_total_km
    FROM vehicles_model
""").fetchdf()
con.close()

print(f"Rows: {len(df):,} | countries: {df['country'].nunique()} | vehicle families: {df['vehicle_family'].nunique()}")

df["log_dist"] = np.log(df["dist_total_km"])

if ref.upper() == "EU":
    # sum-to-zero coding: each coefficient = deviation from the cross-country average
    formula = "gap_log ~ C(country, contr.sum) + log_dist | vehicle_family"
else:
    formula = f"gap_log ~ i(country, ref='{ref.upper()}') + log_dist | vehicle_family"

m = pf.feols(formula, data=df, vcov={"CRV1": "vehicle_family"})
print(m.summary())

coefs = m.coef()
ses = m.se()
res = pd.DataFrame({"coef": coefs, "se": ses})
res = res[res.index.str.contains("country")]
res["pct_vs_ref"] = (np.exp(res["coef"]) - 1) * 100
res["ci_low_pct"] = (np.exp(res["coef"] - 1.96 * res["se"]) - 1) * 100
res["ci_high_pct"] = (np.exp(res["coef"] + 1.96 * res["se"]) - 1) * 100
res = res.sort_values("pct_vs_ref")

out_path = ROOT / "db" / f"country_effects_ref_{ref.upper()}.csv"
res.to_csv(out_path)
print(f"\nSaved: {out_path}")
print(res[["pct_vs_ref", "ci_low_pct", "ci_high_pct"]].round(2).to_string())
