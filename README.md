# Niger Anticipatory Action: Drought

Analysis for drought anticipatory action in Niger.

## Interactive trigger explorer

The primary deliverable is an interactive [marimo](https://marimo.io) app that lets you
explore the two-component drought trigger and see how threshold choices affect the
historical activation record.

- **Source:** `exploration/rolling_threshold_marimo.py`
- **Deployed:** exported to WASM in `docs/` and served via GitHub Pages from the
  `iri-trend` branch (`docs/` folder).
- **Static snapshot:** a non-interactive HTML export at the default sliders
  (forecast 35 %, observational 15 %) is served at
  [`/static/`](https://ocha-dap.github.io/ds-aa-ner-drought/static/)
  (`docs/static/index.html`). Regenerate with
  `uv run marimo export html exploration/rolling_threshold_marimo.py --no-include-code -o docs/static/index.html`.

### Trigger design

A year triggers if **either** component fires (logical OR):

- **Forecast component** — IRI forecast probabilities (OCHA Certification model, 35%
  frequency). Triggers if any two *consecutive* months (Jan+Feb, …, May+Jun) both land in
  the top *X%* of their **rolling 10-year** historical reference window.
- **Observational component** — ENACTS MON Jun–Jul SPI (labelled `Aug` in the export).
  Triggers if the value is in the bottom *Y%* of the **full historical** record (a single
  fixed threshold, not rolling).

Defaults: forecast 35%, observational 15%. Target combined return period ≈ 3.5 years.

### Threshold percentile convention

Thresholds are **locked to actual historical values** — no interpolation between data
points. For a percentile *p* over a window of *n* values, the threshold is the *k*-th most
extreme observed value where `k = ceil(p/100 × n)`:

- Forecast (10-yr window): 5–10% → k=1, 15–20% → k=2, 25–30% → k=3, 35–40% → k=4, …
- Observational: same formula over the full record.
- `p = 0` never triggers (threshold ±∞).

Because of the `ceil`, adjacent 5% slider steps can yield identical thresholds for a
10-year window — this is the honest consequence of discretising onto real observations.

### App layout

1. **Top:** two threshold sliders, return-period readout, trigger-count and bad-year
   correlation bar charts, the 6-month forecast grid, and the observational plot.
2. **Activation record:** per-year trigger table with a "Bad year" rank column
   (colour-coded by severity percentile).
3. **Optimization (bottom):** methodology notes, the full percentile sweep / RP table,
   automatic threshold selection, and a single-month interactive detail chart.

"Bad year" ranks come from an external severity list (lower rank = worse year) and are
used to check whether each component preferentially fires in genuinely bad years.

## Development

Environment is managed with [`uv`](https://docs.astral.sh/uv/).

```bash
# Run the app locally (loads data from Azure blob via ocha-stratus)
uv run marimo run exploration/rolling_threshold_marimo.py

# Edit interactively
uv run marimo edit exploration/rolling_threshold_marimo.py

# Re-export to the deployed WASM bundle after changes
uv run marimo export html-wasm exploration/rolling_threshold_marimo.py \
    --mode run -o docs/index.html
```

When running locally the notebook loads the source CSV from Azure blob storage via
`ocha-stratus`. In the browser (WASM) it falls back to the bundled
`docs/public/iri_data.csv`, so re-run the export whenever the data or notebook changes.

### Data source

Historical IRI forecasts exported from the Maproom on **25 April 2026**, OCHA
Certification model, frequency slider at **35%**. Blob path:
`ds-aa-ner-drought/raw/iri/ner_maproom_export_2026-04-25_thresh35 - Sheet1.csv`.

## 2026 Jun–Jul rainfall monitoring page

A static, self-contained page at
[`/rainfall/`](https://ocha-dap.github.io/ds-aa-ner-drought/rainfall/)
(`docs/rainfall/index.html`) tracks how close the 2026 season is to the
observational trigger threshold using ERA5 and CHIRPS as proxies for the
not-yet-available ENACTS Jun–Jul SPI:

- **Data prep:** `exploration/jun_jul_rainfall_make_data.py` — reads ERA5
  monthly COGs from the team prod raster blob and CHIRPS v2.0 Africa
  monthly from CHC, computes the Jun–Jul zonal mean over Niger south of
  17°N (1981–2026), and writes
  `exploration/public/junjul_rainfall.csv` + map grids
  (`junjul_rainfall_grids_2026.npz`), plus a CSV copy to blob under
  `ds-aa-ner-drought/processed/rainfall/`.
- **Page renderer:** `exploration/jun_jul_rainfall_page.py` — plain
  HTML with embedded matplotlib figures (no marimo).
- **Regenerate:**
  `uv run python exploration/jun_jul_rainfall_make_data.py` then
  `uv run python exploration/jun_jul_rainfall_page.py`.

## 2026 drought-pockets page

A static, bilingual (EN/FR toggle) page at
[`/pockets/`](https://ocha-dap.github.io/ds-aa-ner-drought/pockets/)
(`docs/pockets/index.html`) maps where drought could be emerging in the
2026 season, expressing every indicator as an empirical return period per
department and overlaying 2026 HNRP severity:

- **Indicators:** CHIRPS Jun–Jul and IMERG Jun–Aug rainfall (per-adm2
  zonal, plus a CHIRPS pixel percentile map), DMN rain gauges via OGIMET
  CLIMAT, FAO ASIS ASI/VHI per region, and the SEAS5 issued-August
  forecast (skill methodology reused from `ds-seas5-skill`, including the
  in-season JAS composite recomputed with 2026 ERA5).
- **Fetch:** `exploration/pockets_fetch_chirps.py`,
  `pockets_fetch_gauges.py`, `pockets_fetch_seas5.py`,
  `pockets_fetch_other.py` (ASIS, IMERG/ERA5 DB, HNRP, CODAB) — all into
  `exploration/public/pockets/`.
- **Analysis:** `exploration/pockets_build_summary.py` (Weibull return
  periods, 4-indicator convergence count).
- **Page:** `exploration/pockets_figures.py` +
  `exploration/pockets_page.py` (plain HTML, embedded matplotlib figures,
  D86-style EN/FR toggle; no marimo).
- **Regenerate:** run the four fetch scripts, then
  `uv run python exploration/pockets_build_summary.py`, then
  `cd exploration && uv run python pockets_page.py`.

## Other files

- `exploration/detrending_marimo.py` — earlier detrending-based trigger exploration.
- `index.qmd`, `_quarto.yml`, `_freeze/` — legacy Quarto report (publish workflow
  disabled; superseded by the marimo app for GitHub Pages).
