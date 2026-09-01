"""Fetch CHIRPS v2.0 Africa monthly rasters and build Niger Jun+Jul stacks.

Downloads Jun and Jul monthly GeoTIFFs 1981-2026 from the Climate Hazards
Center (cached locally), clips to the Niger bounding box, and writes:

- ``exploration/public/pockets/chirps_junjul_stack.npz`` — per-year Jun+Jul
  total grids over Niger (0.05 deg), plus lon/lat axes.
- ``exploration/public/pockets/chirps_junjul_adm2.csv`` — zonal mean Jun+Jul
  total per admin-2 department per year.

Usage: ``uv run python exploration/pockets_fetch_chirps.py``
"""

import gzip
import os
import urllib.request
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd
import rioxarray as rxr
from rasterio.features import rasterize

YEARS = range(1981, 2027)
MONTHS = (6, 7)
# generous box around Niger (0.15W-16.0E, 11.7-23.5N)
BBOX = (-0.5, 11.0, 16.5, 24.0)

CHIRPS_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
CHIRPS_CACHE = Path(
    os.getenv(
        "CHIRPS_CACHE_DIR", Path.home() / ".cache" / "chirps_africa_monthly"
    )
)
OUT_DIR = Path(__file__).parent / "public" / "pockets"


def chirps_month(year, month):
    CHIRPS_CACHE.mkdir(parents=True, exist_ok=True)
    path = CHIRPS_CACHE / f"chirps-v2.0.{year}.{month:02d}.tif"
    if not path.exists():
        url = CHIRPS_URL.format(year=year, month=month)
        with urllib.request.urlopen(url, timeout=120) as resp:
            path.write_bytes(gzip.decompress(resp.read()))
    da = rxr.open_rasterio(path).squeeze(drop=True)
    da = da.rio.write_crs("EPSG:4326")
    sub = da.sel(x=slice(BBOX[0], BBOX[2]), y=slice(BBOX[3], BBOX[1]))
    return sub.where(sub != -9999)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    adm2 = stratus.codab.load_codab_from_blob("ner", admin_level=2)

    # per-pixel admin-2 index grid, built on the first year's raster
    template = chirps_month(1981, 6)
    shapes = [(geom, i) for i, geom in enumerate(adm2.geometry.values)]
    admin_idx = rasterize(
        shapes,
        out_shape=template.shape,
        transform=template.rio.transform(),
        fill=-1,
        dtype="int32",
    )

    grids = {}
    rows = []
    years_done = []
    for year in YEARS:
        try:
            total = (chirps_month(year, 6) + chirps_month(year, 7)).values
        except Exception as e:
            print(f"skip {year}: {e}", flush=True)
            continue
        grids[f"y{year}"] = total.astype("float32")
        years_done.append(year)
        for i, pcode in enumerate(adm2["ADM2_PCODE"].values):
            m = (admin_idx == i) & np.isfinite(total)
            if m.sum() == 0:
                continue
            rows.append(
                {
                    "pcode": pcode,
                    "year": year,
                    "junjul_mm": float(total[m].mean()),
                    "n_pix": int(m.sum()),
                }
            )
        print(f"chirps {year} ok", flush=True)

    np.savez_compressed(
        OUT_DIR / "chirps_junjul_stack.npz",
        lons=template.x.values,
        lats=template.y.values,
        years=np.array(years_done),
        admin_idx=admin_idx,
        **grids,
    )
    pd.DataFrame(rows).to_csv(OUT_DIR / "chirps_junjul_adm2.csv", index=False)
    print(f"done: {len(years_done)} years, {len(rows)} adm2 rows", flush=True)


if __name__ == "__main__":
    main()
