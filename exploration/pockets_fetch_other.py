"""Fetch the remaining inputs for the 2026 drought-pockets analysis.

- IMERG daily precip per admin-2 from the prod DB (``public.imerg``,
  zonal means maintained by the raster-stats pipeline) -> Jun-Aug
  season-to-date totals per year, 2001-2026.
- ERA5 monthly per admin-2 from ``public.era5`` -> Jun+Jul totals per year.
- FAO ASIS Agricultural Stress Index (ASI) and Vegetation Health Index
  (VHI) dekadal CSVs per region (GIEWS Earth Observation, open data).
- 2026 HNRP JIAF intersectoral severity + PiN per department from the
  team's HPC mirror (``hpc.severity_admin`` / ``hpc.pin_admin``, dev DB).
- CODAB admin boundaries cached to a local GeoPackage.

All outputs land in ``exploration/public/pockets/``.

Usage: ``uv run python exploration/pockets_fetch_other.py``
"""

import calendar
import urllib.request
from pathlib import Path

import ocha_stratus as stratus
import pandas as pd

OUT_DIR = Path(__file__).parent / "public" / "pockets"

ASIS_BASE = "https://www.fao.org/giews/earthobservation/asis/data/country/NER"
ASIS_FILES = {
    "asi_dekad.csv": "MAP_ASI/DATA/ASI_Dekad_Season1_data.csv",
    "vhi_dekad.csv": "MAP_NDVI_ANOMALY/DATA/vhi_adm1_dekad_data.csv",
    "mvhi_dekad.csv": "MAP_ASI/DATA/MVHI_Dekad_Season1_data.csv",
}
# latest complete dekad at time of analysis: 2026 dekad 23 (11-20 Aug)
ASIS_MAPS = {
    "fao_asi_map.png": "MAP_ASI/HR/ot2623h_aC1_s1_g2.png",
    "fao_ndvi_anom_map.png": "MAP_NDVI_ANOMALY/HR/ot2623n.png",
}


def fetch_asis():
    for name, rel in {**ASIS_FILES, **ASIS_MAPS}.items():
        path = OUT_DIR / name
        if path.exists():
            continue
        req = urllib.request.Request(
            f"{ASIS_BASE}/{rel}", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
        print(f"asis {name} ok", flush=True)


def fetch_db():
    eng = stratus.get_engine(stage="prod")
    with eng.connect() as con:
        imerg = pd.read_sql(
            "SELECT pcode, valid_date, mean FROM public.imerg "
            "WHERE iso3='NER' AND adm_level=2 "
            "AND EXTRACT(month FROM valid_date) IN (6,7,8)",
            con,
        )
        era5 = pd.read_sql(
            "SELECT pcode, valid_date, mean FROM public.era5 "
            "WHERE iso3='NER' AND adm_level=2 "
            "AND EXTRACT(month FROM valid_date) IN (6,7)",
            con,
        )

    imerg["valid_date"] = pd.to_datetime(imerg["valid_date"])
    imerg["year"] = imerg["valid_date"].dt.year
    imerg["doy_ok"] = imerg["valid_date"].dt.strftime("%m-%d") <= "08-30"
    # keep Jun 1 - Aug 30 in every year so 2026 (data through Aug 30) compares
    # like-for-like
    seas = (
        imerg[imerg["doy_ok"]]
        .groupby(["pcode", "year"])
        .agg(junaug_mm=("mean", "sum"), n_days=("mean", "size"))
        .reset_index()
    )
    seas = seas[seas["n_days"] >= 85]  # 91 days nominal; tolerate small gaps
    seas.to_csv(OUT_DIR / "imerg_junaug_adm2.csv", index=False)
    print(f"imerg: {len(seas)} pcode-years", flush=True)

    era5["valid_date"] = pd.to_datetime(era5["valid_date"])
    era5["year"] = era5["valid_date"].dt.year
    era5["mm"] = era5.apply(
        lambda r: r["mean"]
        * calendar.monthrange(r["year"], r["valid_date"].month)[1],
        axis=1,
    )
    e = (
        era5.groupby(["pcode", "year"])
        .agg(junjul_mm=("mm", "sum"), n_months=("mm", "size"))
        .reset_index()
    )
    e = e[e["n_months"] == 2]
    e.to_csv(OUT_DIR / "era5_junjul_adm2.csv", index=False)
    print(f"era5: {len(e)} pcode-years", flush=True)

    eng2 = stratus.get_engine(stage="dev")
    with eng2.connect() as con:
        sev = pd.read_sql(
            "SELECT admin1_code, admin1_name, admin2_code, admin2_name, "
            "population, final_severity FROM hpc.severity_admin "
            "WHERE iso3='NER' AND year=2026",
            con,
        )
        pin = pd.read_sql(
            "SELECT admin2_code, final_pin FROM hpc.pin_admin "
            "WHERE iso3='NER' AND year=2026",
            con,
        )
    hnrp = sev.merge(pin, on="admin2_code", how="left")
    hnrp.to_csv(OUT_DIR / "hnrp_2026_adm2.csv", index=False)
    print(f"hnrp: {len(hnrp)} departments", flush=True)


def fetch_codab():
    for level in (1, 2):
        path = OUT_DIR / f"ner_adm{level}.gpkg"
        if path.exists():
            continue
        gdf = stratus.codab.load_codab_from_blob("ner", admin_level=level)
        gdf.to_file(path, driver="GPKG")
        print(f"codab adm{level} ok", flush=True)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fetch_asis()
    fetch_codab()
    fetch_db()
    print("done", flush=True)
