"""
Build a local DuckDB database from the raw JRC OBFCM CSV.

Why DuckDB: single embedded file (like SQLite, no server), columnar storage
(the 2.1GB CSV compresses to a fraction of that), fast SQL aggregations over
7.7M rows, and readable from Python/R/JS/CLI by any downstream tool without
re-parsing the CSV each time.

Source: dataset/obfcm_M1_2021_2023_concatenated_unique_vehicles.csv
Output: db/obfcm.duckdb
"""
import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "dataset" / "obfcm_M1_2021_2023_concatenated_unique_vehicles.csv"
DB_PATH = ROOT / "db" / "obfcm.duckdb"
DB_PATH.parent.mkdir(exist_ok=True)

con = duckdb.connect(str(DB_PATH))

# --- raw table: typed + renamed to clean snake_case, source column noted in comments ---
con.execute(f"""
CREATE OR REPLACE TABLE vehicles AS
SELECT
    veh_id::BIGINT                          AS veh_id,
    "OBFCM data source"::VARCHAR            AS obfcm_source,          -- OEM / Member State
    OBFCM_ReportingPeriod::SMALLINT         AS reporting_period,
    OBFCM_TotLifetimeFuel_l::DOUBLE         AS fuel_total_l,
    OBFCM_TotLifetimeDist_km::DOUBLE        AS dist_total_km,
    OBFCM_ChargeDeplOprEngineOff_km::DOUBLE AS phev_dist_cd_engine_off_km,
    OBFCM_ChargeDeplOprEngineOn_km::DOUBLE  AS phev_dist_cd_engine_on_km,
    OBFCM_ChargeIncrOpr_km::DOUBLE          AS phev_dist_ci_km,
    OBFCM_ChargeDeplFuel_l::DOUBLE          AS phev_fuel_cd_l,
    OBFCM_ChargeIncrFuel_l::DOUBLE          AS phev_fuel_ci_l,
    OBFCM_EnergyIntoBattery_kWh::DOUBLE     AS phev_energy_into_battery_kwh,
    EEA_year::SMALLINT                      AS reg_year,
    EEA_MS::VARCHAR                         AS country,               -- Member State of registration (ISO-2)
    EEA_VFN::VARCHAR                        AS vehicle_family,        -- type-approval family, used as "model" FE
    EEA_Fm::VARCHAR                         AS fuel_mode,             -- M=ICEV, H=HEV, P=PHEV
    EEA_Ft::VARCHAR                         AS fuel_type,             -- PETROL / DIESEL / *_ELECTRIC (PHEV)
    EEA_Mh::VARCHAR                         AS manufacturer,
    EEA_Mp::VARCHAR                         AS manufacturer_pool,
    EEA_Cn::VARCHAR                         AS commercial_name,
    EEA_M::DOUBLE                           AS mass_running_kg,
    EEA_Mt::DOUBLE                          AS mass_test_kg,
    EEA_Ewltp::DOUBLE                       AS co2_wltp_g_km,
    EEA_Fc::DOUBLE                          AS fc_wltp_l_100km,       -- official/WLTP fuel consumption
    EEA_Ec::DOUBLE                          AS engine_capacity_cm3,
    EEA_Ep::DOUBLE                          AS engine_power_kw,
    EEA_Z::DOUBLE                           AS elec_consumption_wltp_wh_km,
    EEA_Zr::DOUBLE                          AS elec_range_wltp_km,
    vdb_max_passengers::SMALLINT            AS max_passengers,
    vdb_vehicle_length::DOUBLE              AS vehicle_length_m,
    vdb_vehicle_width::DOUBLE               AS vehicle_width_m,
    vdb_vehicle_height::DOUBLE              AS vehicle_height_m,
    vdb_ground_clearance::DOUBLE            AS ground_clearance_m,
    vdb_front_tyre_radius::DOUBLE           AS front_tyre_radius_m,
    vdb_gear_box_type::VARCHAR              AS gearbox_type,
    RW_CO2::DOUBLE                          AS co2_real_g_km,
    RW_FC::DOUBLE                           AS fc_real_l_100km,       -- real-world fuel consumption (JRC-computed)
    RW_EC::DOUBLE                           AS ec_real_kwh_100km,
    RW_eds::DOUBLE                          AS electric_driving_share_pct,
    gap::DOUBLE                             AS gap_co2_abs_g_km,      -- JRC-computed CO2 gap, for sanity-check
    gap_percentage::DOUBLE                  AS gap_co2_pct
FROM read_csv_auto('{CSV_PATH.as_posix()}')
ORDER BY country, vehicle_family
""")

n = con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
print(f"vehicles table: {n:,} rows")

# --- analysis-ready subset for the phase-1 model ---
# Filters per CLAUDE.md: exclude PHEV, min 3000 km lifetime distance, drop
# real/WLTP ratio outliers (<0.7 or >2). fuel_mode != 'P' is equivalent to and
# clearer than filtering on fuel_type, since PHEV rows are exactly fuel_mode = 'P'.
con.execute("""
CREATE OR REPLACE TABLE vehicles_model AS
SELECT
    *,
    fc_real_l_100km / fc_wltp_l_100km          AS ratio_real_wltp,
    ln(fc_real_l_100km / fc_wltp_l_100km)      AS gap_log
FROM vehicles
WHERE fuel_mode IN ('M', 'H')
  AND dist_total_km >= 3000
  AND (fc_real_l_100km / fc_wltp_l_100km) BETWEEN 0.7 AND 2
""")

n_model = con.execute("SELECT COUNT(*) FROM vehicles_model").fetchone()[0]
print(f"vehicles_model table (ICEV+HEV, cleaned): {n_model:,} rows")

con.close()
print(f"Database written to {DB_PATH}")
