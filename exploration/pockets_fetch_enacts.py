"""Fetch ENACTS MON Jun-Jul SPI per Niger admin unit from the IRI Maproom.

The fbfmaproom2 export API (public, no auth — the same endpoint behind the
framework's Maproom, see the ENACTS investigation notes) accepts admin
levels: ``mode=0&region=NE`` (the monitored zone), ``mode=1&region=NE00x``
(regions) and ``mode=2&region=NExxxyyy`` (departments, CODAB pcodes). Pixel
mode is explicitly unsupported by the endpoint, and the map tiles carry a
region-uniform fill, so department level is the finest ENACTS access
available without IRI Data Library credentials.

Northern desert units return HTTP 500 (no ENACTS coverage) and are skipped.
Responses are cached under ``exploration/public/pockets/enacts_cache``.

Output: ``exploration/public/pockets/enacts_spi_adm.csv`` —
level (zone/1/2), pcode, year, spi (1991-2026).

Usage: ``uv run python exploration/pockets_fetch_enacts.py``
"""

import json
import time
import urllib.request
from pathlib import Path

import ocha_stratus as stratus
import pandas as pd

OUT_DIR = Path(__file__).parent / "public" / "pockets"
CACHE = OUT_DIR / "enacts_cache"

URL = (
    "https://iridl.ldeo.columbia.edu/fbfmaproom2/niger/export"
    "?season=season1&issue_month=may&freq=15"
    "&predictor=enacts-mon-spi-jj&predictand=bad-years-v3"
    "&include_upcoming=true&mode={mode}&region={region}"
)


def fetch(mode, region):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{mode}_{region}.json"
    if path.exists():
        return json.loads(path.read_text())
    req = urllib.request.Request(
        URL.format(mode=mode, region=region),
        headers={"User-Agent": "Mozilla/5.0 (research; OCHA CHD)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"{mode}/{region}: {e}", flush=True)
        return None
    path.write_text(json.dumps(data))
    time.sleep(1.5)
    return data


def main():
    adm1 = stratus.codab.load_codab_from_blob("ner", admin_level=1)
    adm2 = stratus.codab.load_codab_from_blob("ner", admin_level=2)
    units = [("zone", "0", "NE")]
    units += [("1", "1", p) for p in adm1["ADM1_PCODE"]]
    units += [("2", "2", p) for p in adm2["ADM2_PCODE"]]

    rows = []
    for level, mode, pcode in units:
        data = fetch(mode, pcode)
        if data is None:
            continue
        for h in data["history"]:
            spi = h.get("enacts-mon-spi-jj")
            if spi is None or pd.isna(spi):
                continue
            rows.append(
                {
                    "level": level,
                    "pcode": pcode,
                    "year": h["year"],
                    "spi": spi,
                }
            )
        print(f"{level}/{pcode}: ok", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "enacts_spi_adm.csv", index=False)
    print(f"wrote {len(df)} rows, {df['pcode'].nunique()} units", flush=True)


if __name__ == "__main__":
    main()
