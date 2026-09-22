"""
Download the raw JRC OBFCM dataset into dataset/.

Source: JRC OBFCM M1 2021-2023, CC BY 4.0
https://data.jrc.ec.europa.eu/dataset/9528c82b-37fa-4da3-9b6b-b54eaf0ba4ac

The CSV is ~2.1GB and is gitignored — run this once locally before
scripts/01_build_database.py.
"""
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
DATASET_DIR.mkdir(exist_ok=True)

FILES = {
    "obfcm_M1_2021_2023_concatenated_unique_vehicles.csv":
        "https://code.europa.eu/jrc-legent/legent-data/-/raw/main/OBFCM/light_duty_vehicles/"
        "obfcm_M1_2021_2023_concatenated_unique_vehicles.csv?inline=false",
    "obfcm_M1_2021_2023_table_description.xlsx":
        "https://code.europa.eu/jrc-legent/legent-data/-/raw/main/OBFCM/light_duty_vehicles/"
        "obfcm_M1_2021_2023_table_description.xlsx?inline=false",
}

for filename, url in FILES.items():
    dest = DATASET_DIR / filename
    if dest.exists():
        print(f"Already present, skipping: {dest}")
        continue
    print(f"Downloading {filename} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"  -> {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
