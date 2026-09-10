"""Build Jun-Jul seasonal rainfall series for Niger (south of 17degN).

Two sources, used as proxies for the ENACTS-based observational trigger
indicator (the Maproom Jun-Jul SPI), which is not yet available for 2026:

- ERA5 reanalysis: monthly precipitation COGs maintained by the team's
  raster pipeline on the prod ``raster`` container
  (``era5/monthly/processed/precip_reanalysis_vYYYY-MM-01.tif``, mm/day).
- CHIRPS v2.0: Africa monthly GeoTIFFs from the Climate Hazards Center
  (mm/month), downloaded on the fly and cached locally.

The zonal statistic is the pixel mean over Niger's admin-0 boundary
clipped to latitudes south of 17degN (the monitored zone of the Niger
drought AA framework).

Outputs:
- blob (dev/projects):
  ``ds-aa-ner-drought/processed/rainfall/ner_junjul_rainfall_era5_chirps.csv``
- ``exploration/public/junjul_rainfall.csv`` — same CSV, bundled for the
  marimo page.
- ``exploration/public/junjul_rainfall_grids_2026.npz`` — 2026 seasonal
  totals and 1991-2020 climatology grids (plus boundary polylines) for
  the maps on the page.

Usage: ``uv run python exploration/jun_jul_rainfall_make_data.py``
Set ``CHIRPS_CACHE_DIR`` to override the CHIRPS download cache
(default ``~/.cache/chirps_africa_monthly``).
"""

import calendar
import gzip
import os
import urllib.request
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd
import rioxarray as rxr
from shapely.geometry import box

YEARS = range(1981, 2027)
MONTHS = (6, 7)
CLIMO_YEARS = range(1991, 2021)
CURRENT_YEAR = 2026
LAT_CUTOFF = 17.0
BBOX = (-1.0, 11.0, 17.0, 18.0)  # lon_min, lat_min, lon_max, lat_max

CHIRPS_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
CHIRPS_CACHE = Path(
    os.getenv(
        "CHIRPS_CACHE_DIR", Path.home() / ".cache" / "chirps_africa_monthly"
    )
)

BLOB_CSV = (
    "ds-aa-ner-drought/processed/rainfall/"
    "ner_junjul_rainfall_era5_chirps.csv"
)
PUBLIC_DIR = Path(__file__).parent / "public"


def get_mask_geom():
    adm0 = stratus.codab.load_codab_from_blob("ner", admin_level=0)
    full = adm0.geometry.iloc[0]
    below17 = full.intersection(box(BBOX[0], 0, BBOX[2], LAT_CUTOFF))
    return full, below17


def boundary_polyline(geom):
    """Exterior ring(s) as one (n, 2) array, NaN rows between rings."""
    geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
    parts = []
    for g in geoms:
        parts.append(np.asarray(g.exterior.coords))
        parts.append(np.full((1, 2), np.nan))
    return np.vstack(parts[:-1])


def clip_to_mask(da, geom):
    da = da.squeeze(drop=True).rio.write_crs("EPSG:4326")
    sub = da.sel(x=slice(BBOX[0], BBOX[2]), y=slice(BBOX[3], BBOX[1]))
    return sub.rio.clip([geom])


def era5_month(year, month, geom, container_client):
    blob = (
        "era5/monthly/processed/"
        f"precip_reanalysis_v{year}-{month:02d}-01.tif"
    )
    da = stratus.open_blob_cog(
        blob,
        stage="prod",
        container_name="raster",
        container_client=container_client,
    )
    mm_day = clip_to_mask(da, geom)
    return mm_day * calendar.monthrange(year, month)[1]


def chirps_month(year, month, geom):
    CHIRPS_CACHE.mkdir(parents=True, exist_ok=True)
    path = CHIRPS_CACHE / f"chirps-v2.0.{year}.{month:02d}.tif"
    if not path.exists():
        url = CHIRPS_URL.format(year=year, month=month)
        with urllib.request.urlopen(url) as resp:
            path.write_bytes(gzip.decompress(resp.read()))
    da = rxr.open_rasterio(path)
    da = da.where(da != -9999)
    return clip_to_mask(da, geom)


def main():
    full_adm0, mask_geom = get_mask_geom()
    era5_cc = stratus.get_container_client("raster", stage="prod")

    rows = []
    grids = {}
    for source in ("era5", "chirps"):
        climo_sum = None
        climo_n = 0
        for year in YEARS:
            monthly = {}
            try:
                for month in MONTHS:
                    if source == "era5":
                        monthly[month] = era5_month(
                            year, month, mask_geom, era5_cc
                        )
                    else:
                        monthly[month] = chirps_month(year, month, mask_geom)
            except Exception as e:  # missing month -> skip year
                print(f"skip {source} {year}: {e}")
                continue
            seasonal = monthly[6] + monthly[7]
            rows.append(
                {
                    "source": source,
                    "year": year,
                    "jun_mm": float(monthly[6].mean()),
                    "jul_mm": float(monthly[7].mean()),
                    "seasonal_mm": float(seasonal.mean()),
                }
            )
            if year in CLIMO_YEARS:
                climo_sum = (
                    seasonal if climo_sum is None else climo_sum + seasonal
                )
                climo_n += 1
            if year == CURRENT_YEAR:
                grids[f"{source}_total_2026"] = seasonal.values.astype(
                    "float32"
                )
                grids[f"{source}_lons"] = seasonal.x.values
                grids[f"{source}_lats"] = seasonal.y.values
            print(f"{source} {year}: {rows[-1]['seasonal_mm']:.1f} mm")
        grids[f"{source}_climo"] = (climo_sum / climo_n).values.astype(
            "float32"
        )

    df = pd.DataFrame(rows)
    PUBLIC_DIR.mkdir(exist_ok=True)
    df.to_csv(PUBLIC_DIR / "junjul_rainfall.csv", index=False)
    stratus.upload_csv_to_blob(df, BLOB_CSV, stage="dev")

    grids["adm0_boundary"] = boundary_polyline(full_adm0)
    grids["mask_boundary"] = boundary_polyline(mask_geom)
    np.savez_compressed(PUBLIC_DIR / "junjul_rainfall_grids_2026.npz", **grids)
    print(f"wrote {len(df)} rows; grids: {sorted(grids)}")


if __name__ == "__main__":
    main()
