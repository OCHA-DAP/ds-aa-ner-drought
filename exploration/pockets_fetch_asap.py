"""Fetch the current JRC ASAP warnings for Niger (GAUL2 units).

The EC/JRC ASAP system (agricultural-production-hotspots.ec.europa.eu —
NOT the same product as FAO ASIS) publishes automated agricultural-drought
warnings per admin unit x landcover every dekad. This pulls the current
warning layers with geometries from ASAP's public WFS, filtered to Niger:

  public:warning_gaul2_crop / public:warning_gaul2_rangeland

Outputs ``exploration/public/pockets/asap_warnings_{crop,rangeland}.geojson``
(one feature per ASAP GAUL2 unit: warning code ``w_*``, label ``w_*_na``,
colour group ``w_*_gr``, and the classification dekad in ``date``).

Usage: ``uv run python exploration/pockets_fetch_asap.py``
"""

import json
from pathlib import Path

import requests

OUT_DIR = Path(__file__).parent / "public" / "pockets"
BASE = "https://agricultural-production-hotspots.ec.europa.eu/public/ows"


def fetch_layer(landcover):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"public:warning_gaul2_{landcover}",
        "outputFormat": "application/json",
        "cql_filter": "asap0_name='Niger'",
    }
    r = requests.get(
        BASE,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    path = OUT_DIR / f"asap_warnings_{landcover}.geojson"
    path.write_text(json.dumps(data))
    dates = {f["properties"]["date"] for f in data["features"]}
    print(f"{landcover}: {len(data['features'])} units, dekad(s) {dates}")
    return data


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for lc in ("crop", "rangeland"):
        data = fetch_layer(lc)
        key = "w_crop" if lc == "crop" else "w_range"
        labels = {
            (
                f["properties"].get(key),
                f["properties"].get(f"{key}_na"),
                f["properties"].get(f"{key}_gr"),
            )
            for f in data["features"]
        }
        for code in sorted(labels, key=lambda t: (t[0] is None, t[0])):
            print("  ", code)
