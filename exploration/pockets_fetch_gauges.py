"""Fetch Niger rain-gauge monthly totals from OGIMET (GTS CLIMAT reports).

CLIMAT is the WMO monthly summary each national met service (here DMN Niger)
transmits over the GTS; OGIMET archives it from ~2005. This pulls the
country-wide CLIMAT table for Jun/Jul/Aug of each year 2005-2026, plus — for
months whose CLIMAT has not yet arrived (Aug 2026 right after month end) — a
provisional total summed from daily SYNOP reports.

Raw HTML responses are cached under ``exploration/public/pockets/ogimet_cache``
so re-runs cost nothing.

Outputs ``exploration/public/pockets/gauges_monthly.csv``:
station id, name, lat, lon, year, month, precip_mm, n_rain_days, source.

Usage: ``uv run python exploration/pockets_fetch_gauges.py``
"""

import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

YEARS = range(2005, 2027)
MONTHS = (6, 7, 8)
OUT_DIR = Path(__file__).parent / "public" / "pockets"
CACHE = OUT_DIR / "ogimet_cache"

CLIMAT_URL = (
    "https://www.ogimet.com/cgi-bin/gclimat?lang=en&mode=1&state=Niger"
    "&ord=REV&verb=no&year={year}&mes={month:02d}"
)
SYNOP_URL = (
    "https://www.ogimet.com/cgi-bin/gsynres?lang=en&ind={ind}&decoded=yes"
    "&ndays=31&ano={year}&mes={month:02d}&day={day}&hora=06"
)


def fetch(url, cache_name, min_bytes=2000, sleep=4.0):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists() and path.stat().st_size >= min_bytes:
        return path.read_text(errors="replace")
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (research; OCHA CHD)"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  fetch error ({e}), retrying", flush=True)
            time.sleep(20 * (attempt + 1))
            continue
        if "quota" in html.lower() and len(html) < 2000:
            print("  quota hit, backing off 60s", flush=True)
            time.sleep(60)
            continue
        path.write_text(html)
        time.sleep(sleep)
        return html
    return ""


def parse_climat(html):
    """Rows of (wmo_id, name, precip_mm, quintile, n_rain_days) from gclimat.

    The page repeats each station in three tables (monthly summary, day
    counts, extremes); only the FIRST occurrence per station is the CLIMAT
    monthly summary with cells
    name, P0, Sea, H, T, dT, H, Tx, H, Tn, H, E, H, R, Q, nr, H, ...
    where R = monthly precip (mm), Q = WMO quintile code (0-6 vs the 30-yr
    normal; 0 = below the driest, 1 = driest quintile), nr = rain days.
    """
    out = {}
    parts = re.split(r"CAPTION, '(6\d{4}) - ([^(']+)\(Niger\)'\)", html)
    # parts = [head, id1, name1, body1, id2, name2, body2, ...]
    for i in range(1, len(parts) - 2, 3):
        wmo_id, name, body = parts[i], parts[i + 1].strip(" -"), parts[i + 2]
        if wmo_id in out:
            continue  # later tables (day counts / extremes)
        text = re.sub(r"<[^>]+>", "|", body)
        cells = [c.strip() for c in text.split("|") if c.strip()]
        vals = cells[1:20]
        try:
            precip = vals[12]
            q = vals[13]
            nr = vals[14]
            if precip == "Tr":
                precip_mm = 0.0
            elif precip in ("----", ""):
                continue
            else:
                precip_mm = float(precip)
            quintile = int(q) if q.isdigit() else None
            n_days = int(nr) if nr.isdigit() else None
        except (IndexError, ValueError):
            continue
        out[wmo_id] = (wmo_id, name.strip(), precip_mm, quintile, n_days)
    return list(out.values())


def parse_station_coords(html):
    """(lat, lon) decimal degrees from a gsynres header, or None."""
    m = re.search(
        r"Latitude[^0-9]*(\d+)-(\d+)(?:-(\d+))?\s*([NS])[^L]*"
        r"Longitude[^0-9]*(\d+)-(\d+)(?:-(\d+))?\s*([EW])",
        html,
    )
    if not m:
        return None
    lat = int(m.group(1)) + int(m.group(2)) / 60 + int(m.group(3) or 0) / 3600
    lon = int(m.group(5)) + int(m.group(6)) / 60 + int(m.group(7) or 0) / 3600
    if m.group(4) == "S":
        lat = -lat
    if m.group(8) == "W":
        lon = -lon
    return lat, lon


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in YEARS:
        for month in MONTHS:
            if (year, month) > (2026, 8):
                continue
            html = fetch(
                CLIMAT_URL.format(year=year, month=month),
                f"climat_{year}_{month:02d}.html",
            )
            parsed = parse_climat(html)
            print(f"{year}-{month:02d}: {len(parsed)} stations", flush=True)
            for wmo_id, name, precip, quintile, ndays in parsed:
                rows.append(
                    {
                        "wmo_id": wmo_id,
                        "name": name,
                        "year": year,
                        "month": month,
                        "precip_mm": precip,
                        "quintile": quintile,
                        "n_rain_days": ndays,
                        "source": "CLIMAT",
                    }
                )

    df = pd.DataFrame(rows)

    # station coordinates via one gsynres header each
    coords = {}
    for wmo_id in sorted(df["wmo_id"].unique()):
        html = fetch(
            SYNOP_URL.format(ind=wmo_id, year=2026, month=7, day=31),
            f"gsynres_{wmo_id}.html",
            min_bytes=500,
        )
        c = parse_station_coords(html)
        if c:
            coords[wmo_id] = c
        print(f"coords {wmo_id}: {c}", flush=True)
    df["lat"] = df["wmo_id"].map(lambda i: coords.get(i, (None, None))[0])
    df["lon"] = df["wmo_id"].map(lambda i: coords.get(i, (None, None))[1])

    df.to_csv(OUT_DIR / "gauges_monthly.csv", index=False)
    print(f"wrote {len(df)} rows", flush=True)


if __name__ == "__main__":
    main()
