import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def imports():
    import io
    import sys
    import urllib.request
    from math import ceil
    from pathlib import Path

    import marimo as mo
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    return (
        Path,
        ceil,
        io,
        mcolors,
        mo,
        np,
        pd,
        plt,
        sys,
        urllib,
    )


@app.cell
def header(mo):
    mo.md(
        r"""
        # Niger 2026 Jun–Jul rainfall vs the observational trigger

        **Question:** how likely is the observational arm of the Niger
        drought trigger to fire this year? The arm uses the **ENACTS MON
        Jun–Jul SPI** published on the IRI Maproom, which is not yet
        available to us for 2026. As a stopgap, this page evaluates
        2026 Jun–Jul rainfall over the monitored zone (**Niger south of
        17°N**) in two independent datasets we *do* have — **ERA5**
        reanalysis and **CHIRPS v2.0** — and asks where 2026 falls in
        each dataset's own historical record, relative to the current
        candidate threshold (**driest 15 % of years**, full record,
        value-locked).

        ⚠️ *This is a proxy analysis. The trigger decision is made on the
        ENACTS SPI from the Maproom, not on either of these datasets.*
        """
    )
    return


@app.cell
def load_data(io, mo, np, pd, sys, urllib, Path):
    with mo.status.spinner(subtitle="Loading data..."):
        if sys.platform == "emscripten":
            _base = mo.notebook_location() / "public"

            def _read_bytes(name):
                with urllib.request.urlopen(str(_base / name)) as _r:
                    return _r.read()

            df_rain = pd.read_csv(
                io.StringIO(_read_bytes("junjul_rainfall.csv").decode("utf-8"))
            )
            grids = np.load(
                io.BytesIO(_read_bytes("junjul_rainfall_grids_2026.npz"))
            )
            df_iri = pd.read_csv(
                io.StringIO(_read_bytes("iri_data.csv").decode("utf-8"))
            )
        else:
            _pub = Path(str(mo.notebook_dir())) / "public"
            df_rain = pd.read_csv(_pub / "junjul_rainfall.csv")
            grids = np.load(_pub / "junjul_rainfall_grids_2026.npz")
            df_iri = pd.read_csv(_pub / "iri_data.csv")

    df_iri.columns = [
        "year",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Aug",
        "JAS_SPI",
    ]
    df_iri = df_iri[["year", "Aug"]].astype({"year": int})
    return df_iri, df_rain, grids


@app.cell
def params():
    PCT_DEFAULT = 15
    PCT_ENDORSED = 35
    BASELINE_START = 1991
    BASELINE_END = 2025
    CURRENT_YEAR = 2026
    SOURCES = ["era5", "chirps"]
    SOURCE_LABELS = {"era5": "ERA5", "chirps": "CHIRPS v2.0"}
    return (
        BASELINE_END,
        BASELINE_START,
        CURRENT_YEAR,
        PCT_DEFAULT,
        PCT_ENDORSED,
        SOURCES,
        SOURCE_LABELS,
    )


@app.cell
def threshold_funcs(ceil, np):
    def locked_threshold(values, pct):
        """k-th smallest observed value, k = ceil(pct/100 * n).

        Same value-locked convention as the trigger explorer app: the
        threshold is always an actually-observed historical value.
        """
        values = np.sort(np.asarray(values))
        n = len(values)
        k = ceil(pct / 100 * n)
        if k == 0:
            return -np.inf, 0
        return values[k - 1], k

    def dry_rank(record, value):
        """Rank of `value` among record + value (1 = driest)."""
        allvals = np.append(np.asarray(record), value)
        return int(np.sum(allvals <= value)), len(allvals)

    return dry_rank, locked_threshold


@app.cell
def maps_header(mo):
    mo.md(
        r"""
        ## 2026 Jun–Jul rainfall over the monitored zone

        Left: total Jun–Jul precipitation. Right: the same total as a
        percentage of the 1991–2020 Jun–Jul climatology. The monitored
        zone (Niger south of 17°N, black outline) is the spatial mean
        used everywhere below; the dashed line is 17°N.
        """
    )
    return


@app.cell
def maps(SOURCE_LABELS, SOURCES, grids, mcolors, np, plt):
    _adm0 = grids["adm0_boundary"]
    _mask = grids["mask_boundary"]

    _fig, _axes = plt.subplots(
        len(SOURCES), 2, figsize=(13, 4.2 * len(SOURCES)), dpi=110
    )
    for _i, _src in enumerate(SOURCES):
        _lons = grids[f"{_src}_lons"]
        _lats = grids[f"{_src}_lats"]
        _total = grids[f"{_src}_total_2026"]
        _climo = grids[f"{_src}_climo"]
        with np.errstate(divide="ignore", invalid="ignore"):
            _pct = np.where(_climo > 5, 100 * _total / _climo, np.nan)

        _ax = _axes[_i, 0]
        _pm = _ax.pcolormesh(
            _lons,
            _lats,
            _total,
            cmap="YlGnBu",
            vmin=0,
            vmax=400,
            shading="nearest",
        )
        plt.colorbar(_pm, ax=_ax, label="mm", shrink=0.85)
        _ax.set_title(
            f"{SOURCE_LABELS[_src]} — Jun–Jul 2026 total (mm)", fontsize=11
        )

        _ax2 = _axes[_i, 1]
        _norm = mcolors.TwoSlopeNorm(vmin=0, vcenter=100, vmax=200)
        _pm2 = _ax2.pcolormesh(
            _lons,
            _lats,
            np.clip(_pct, 0, 200),
            cmap="BrBG",
            norm=_norm,
            shading="nearest",
        )
        plt.colorbar(_pm2, ax=_ax2, label="% of 1991–2020 normal", shrink=0.85)
        _ax2.set_title(
            f"{SOURCE_LABELS[_src]} — % of Jun–Jul normal", fontsize=11
        )

        for _ax_ in (_ax, _ax2):
            _ax_.plot(_adm0[:, 0], _adm0[:, 1], color="grey", lw=0.8)
            _ax_.plot(_mask[:, 0], _mask[:, 1], color="black", lw=1.2)
            _ax_.axhline(17, color="black", ls="--", lw=0.8)
            _ax_.set_xlim(-0.5, 16.5)
            _ax_.set_ylim(11.2, 18.2)
            _ax_.set_aspect("equal")
            _ax_.set_xlabel("lon")
            _ax_.set_ylabel("lat")
    _fig.tight_layout()
    _fig
    return


@app.cell
def stats(
    BASELINE_END,
    BASELINE_START,
    CURRENT_YEAR,
    PCT_DEFAULT,
    PCT_ENDORSED,
    SOURCES,
    df_rain,
    dry_rank,
    locked_threshold,
    pd,
):
    stats_rows = []
    records = {}
    for _src in SOURCES:
        _df = df_rain[df_rain["source"] == _src].set_index("year")
        _record = _df.loc[BASELINE_START:BASELINE_END, "seasonal_mm"]
        _val26 = float(_df.loc[CURRENT_YEAR, "seasonal_mm"])
        records[_src] = (_record, _val26)

        _thr15, _k15 = locked_threshold(_record, PCT_DEFAULT)
        _thr35, _k35 = locked_threshold(_record, PCT_ENDORSED)
        _rank, _n_all = dry_rank(_record.values, _val26)
        _rp = (_n_all + 1) / _rank
        stats_rows.append(
            {
                "source": _src,
                "n_record": len(_record),
                "record_median": _record.median(),
                "value_2026": _val26,
                "dry_rank_2026": _rank,
                "n_ranked": _n_all,
                "pctile_2026": 100 * _rank / (_n_all + 1),
                "rp_2026": _rp,
                "thresh_15": _thr15,
                "k_15": _k15,
                "trigger_15": _val26 <= _thr15,
                "margin_15": _val26 - _thr15,
                "thresh_35": _thr35,
                "k_35": _k35,
                "trigger_35": _val26 <= _thr35,
            }
        )
    df_stats = pd.DataFrame(stats_rows).set_index("source")
    return df_stats, records


@app.cell
def series_header(mo):
    mo.md(
        r"""
        ## Historical record and where 2026 falls

        Zonal-mean Jun–Jul rainfall by year. The red line is the
        **15 %** value-locked threshold over the 1991–2025 record; the
        lighter orange line is the endorsed PDF's **35 %** alternative.
        Years at or below the 15 % threshold are circled.
        """
    )
    return


@app.cell
def series_plot(
    BASELINE_END,
    BASELINE_START,
    CURRENT_YEAR,
    SOURCE_LABELS,
    SOURCES,
    df_rain,
    df_stats,
    plt,
):
    _fig, _axes = plt.subplots(
        len(SOURCES), 1, figsize=(11, 3.6 * len(SOURCES)), dpi=110, sharex=True
    )
    for _i, _src in enumerate(SOURCES):
        _ax = _axes[_i]
        _df = df_rain[df_rain["source"] == _src]
        _hist = _df[_df["year"] < CURRENT_YEAR]
        _cur = _df[_df["year"] == CURRENT_YEAR]
        _s = df_stats.loc[_src]

        _ax.plot(
            _hist["year"],
            _hist["seasonal_mm"],
            "-o",
            ms=3.5,
            lw=1,
            color="steelblue",
        )
        _ax.plot(
            _cur["year"],
            _cur["seasonal_mm"],
            "D",
            ms=8,
            color="crimson",
            zorder=5,
            label=f"2026: {_s['value_2026']:.0f} mm",
        )
        _ax.axhline(
            _s["thresh_15"],
            color="crimson",
            lw=1.2,
            label=f"15% threshold: {_s['thresh_15']:.0f} mm",
        )
        _ax.axhline(
            _s["thresh_35"],
            color="orange",
            lw=1,
            ls="--",
            label=f"35% threshold: {_s['thresh_35']:.0f} mm",
        )
        _base = _hist[
            (_hist["year"] >= BASELINE_START) & (_hist["year"] <= BASELINE_END)
        ]
        _below = _base[_base["seasonal_mm"] <= _s["thresh_15"]]
        _ax.plot(
            _below["year"],
            _below["seasonal_mm"],
            "o",
            ms=9,
            mfc="none",
            mec="crimson",
        )
        _ax.axvspan(
            _df["year"].min() - 0.5,
            BASELINE_START - 0.5,
            color="grey",
            alpha=0.12,
        )
        _ax.set_title(
            f"{SOURCE_LABELS[_src]} — Jun–Jul zonal-mean rainfall,"
            " Niger < 17°N",
            fontsize=11,
        )
        _ax.set_ylabel("mm")
        _ax.legend(loc="upper left", fontsize=8)
    _axes[-1].set_xlabel(
        "year (grey band = pre-1991, outside the threshold record)"
    )
    _fig.tight_layout()
    _fig
    return


@app.cell
def summary_table(SOURCE_LABELS, df_stats, mo, pd):
    _rows = []
    for _src, _s in df_stats.iterrows():
        _rows.append(
            {
                "Source": SOURCE_LABELS[_src],
                "2026 Jun–Jul (mm)": f"{_s['value_2026']:.0f}",
                "Record median (mm)": f"{_s['record_median']:.0f}",
                "Dry rank of 2026": (
                    f"{int(_s['dry_rank_2026'])} of {int(_s['n_ranked'])}"
                ),
                "Empirical percentile": f"{_s['pctile_2026']:.0f}%",
                "RP of 2026 dryness": f"{_s['rp_2026']:.1f} yr",
                "15% threshold (mm)": f"{_s['thresh_15']:.0f}",
                "Margin vs 15% (mm)": f"{_s['margin_15']:+.0f}",
                "Triggers at 15%?": "YES" if _s["trigger_15"] else "no",
                "Triggers at 35%?": "YES" if _s["trigger_35"] else "no",
            }
        )
    _df = pd.DataFrame(_rows).set_index("Source")
    mo.vstack(
        [
            mo.md("### 2026 vs the threshold — summary"),
            mo.ui.table(_df.reset_index(), selection=None, pagination=False),
            mo.md(
                "*Dry rank counts 2026 within the 1991–2025 record plus "
                "2026 itself (1 = driest). The return period is the Weibull "
                "plotting position (n+1)/rank of the 2026 value; percentile "
                "= rank/(n+1). A positive margin means 2026 is wetter than "
                "the threshold (no trigger).*"
            ),
        ]
    )
    return


@app.cell
def sweep_table(
    SOURCE_LABELS,
    SOURCES,
    locked_threshold,
    mo,
    pd,
    records,
):
    _rows = []
    for _pct in [5, 10, 15, 20, 25, 30, 35, 40]:
        _row = {"Percentile": f"{_pct}%"}
        for _src in SOURCES:
            _record, _val26 = records[_src]
            _thr, _k = locked_threshold(_record, _pct)
            _row[f"{SOURCE_LABELS[_src]} threshold (mm)"] = f"{_thr:.0f}"
            _row[f"{SOURCE_LABELS[_src]} 2026 triggers?"] = (
                "YES" if _val26 <= _thr else "no"
            )
        _rows.append(_row)
    mo.vstack(
        [
            mo.md(
                "### Sensitivity: would 2026 trigger at other percentile "
                "choices?"
            ),
            mo.ui.table(pd.DataFrame(_rows), selection=None, pagination=False),
        ]
    )
    return


@app.cell
def spi_header(mo):
    mo.md(
        r"""
        ## Cross-check against the actual trigger indicator

        The trigger's observational indicator is the Maproom Jun–Jul SPI
        (the "Aug" column of the trigger dataset, 1991–2025). If ERA5 or
        CHIRPS is to stand in for it, they should co-vary with it. The
        scatter below shows each proxy against the Maproom SPI over the
        common record, with a least-squares fit used to translate the
        2026 proxy value into an implied 2026 SPI.
        """
    )
    return


@app.cell
def spi_compare(
    BASELINE_END,
    BASELINE_START,
    CURRENT_YEAR,
    PCT_DEFAULT,
    SOURCE_LABELS,
    SOURCES,
    df_iri,
    df_rain,
    locked_threshold,
    np,
    pd,
    plt,
    records,
):
    spi_thresh, _k_spi = locked_threshold(df_iri["Aug"], PCT_DEFAULT)

    _fig, _axes = plt.subplots(1, len(SOURCES), figsize=(11, 4.4), dpi=110)
    spi_rows = []
    implied = {}
    for _i, _src in enumerate(SOURCES):
        _ax = _axes[_i]
        _df = df_rain[df_rain["source"] == _src][["year", "seasonal_mm"]]
        _m = _df.merge(df_iri, on="year")
        _m = _m[(_m["year"] >= BASELINE_START) & (_m["year"] <= BASELINE_END)]
        _pearson = float(np.corrcoef(_m["seasonal_mm"], _m["Aug"])[0, 1])
        _spearman = float(
            _m[["seasonal_mm", "Aug"]].corr(method="spearman").iloc[0, 1]
        )
        _b, _a = np.polyfit(_m["seasonal_mm"], _m["Aug"], 1)
        _record, _val26 = records[_src]
        _spi26 = _b * _val26 + _a
        implied[_src] = _spi26
        spi_rows.append(
            {
                "Source": SOURCE_LABELS[_src],
                "Pearson r": f"{_pearson:.2f}",
                "Spearman ρ": f"{_spearman:.2f}",
                "Implied 2026 SPI": f"{_spi26:.3f}",
                "SPI 15% threshold": f"{spi_thresh:.3f}",
                "Implied trigger?": "YES" if _spi26 <= spi_thresh else "no",
            }
        )

        _ax.scatter(_m["seasonal_mm"], _m["Aug"], s=18, color="steelblue")
        _xs = np.linspace(_m["seasonal_mm"].min(), _m["seasonal_mm"].max(), 2)
        _ax.plot(_xs, _b * _xs + _a, color="grey", lw=1)
        _ax.axhline(spi_thresh, color="crimson", lw=1)
        _ax.axvline(_val26, color="crimson", ls="--", lw=1)
        _ax.plot(_val26, _spi26, "D", color="crimson", ms=8, zorder=5)
        _ax.set_title(
            f"{SOURCE_LABELS[_src]} vs Maproom SPI " f"(r={_pearson:.2f})",
            fontsize=11,
        )
        _ax.set_xlabel(f"{SOURCE_LABELS[_src]} Jun–Jul rainfall (mm)")
        _ax.set_ylabel("Maproom Jun–Jul SPI")
    _fig.tight_layout()
    df_spi = pd.DataFrame(spi_rows)
    _fig
    return df_spi, implied, spi_thresh


@app.cell
def spi_table(df_spi, mo):
    mo.vstack(
        [
            mo.ui.table(df_spi, selection=None, pagination=False),
            mo.md(
                "*Red solid line: the 15 % value-locked threshold on the "
                "SPI record itself; red dashed line and diamond: the 2026 "
                "proxy value and its implied SPI. The implied SPI is a "
                "linear translation and carries the fit's uncertainty — "
                "treat it as indicative only.*"
            ),
        ]
    )
    return


@app.cell
def interpretation(
    PCT_DEFAULT,
    SOURCE_LABELS,
    df_stats,
    implied,
    mo,
    spi_thresh,
):
    def _ordinal(n):
        if 10 <= n % 100 <= 20:
            return f"{n}th"
        return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"

    _parts = []
    for _src, _s in df_stats.iterrows():
        _trig = (
            "**would trigger**" if _s["trigger_15"] else "would *not* trigger"
        )
        _parts.append(
            f"- **{SOURCE_LABELS[_src]}**: 2026 is the "
            f"{_ordinal(int(_s['dry_rank_2026']))}"
            f" driest of {int(_s['n_ranked'])} years "
            f"(≈{_s['pctile_2026']:.0f}th percentile, "
            f"1-in-{_s['rp_2026']:.1f}-yr dryness), "
            f"{abs(_s['margin_15']):.0f} mm "
            f"{'below' if _s['margin_15'] <= 0 else 'above'} the "
            f"{PCT_DEFAULT}% threshold → {_trig}. "
            f"Implied Maproom SPI ≈ {implied[_src]:.3f} "
            f"(threshold {spi_thresh:.3f})."
        )
    mo.md(
        "### Bottom line\n\n"
        + "\n".join(_parts)
        + "\n\nBoth proxies put 2026 at or below the 15 % rainfall "
        "threshold, but CHIRPS — much the better-correlated proxy — sits "
        "*exactly at the line*: 6th driest of 36 (the threshold rank), "
        "and its implied SPI lands within a few thousandths of the SPI "
        "threshold. Read this as a **coin-flip-or-better chance** that "
        "the ENACTS value triggers at 15 %, and a near-certain trigger "
        "if the endorsed 35 % threshold is used instead."
    )
    return


@app.cell
def methodology(mo):
    mo.md(
        r"""
        ---
        ### Methodology & caveats

        - **Zone:** Niger admin-0 (FieldMaps CODAB) clipped to south of
          17°N — the monitored zone of the Niger drought AA framework.
          Statistic: unweighted pixel mean over the zone.
        - **ERA5:** monthly total-precipitation COGs from the team raster
          pipeline (prod blob, `era5/monthly/processed/`), mm/day ×
          days-in-month. 1981–2026.
        - **CHIRPS v2.0:** Africa monthly GeoTIFFs from the Climate
          Hazards Center (final product, mm/month). 1981–2026.
        - **Threshold convention:** value-locked, as in the trigger
          explorer — the *k*-th driest observed year where
          *k = ceil(p/100 × n)* over the 1991–2025 record (n = 35;
          p = 15 % → k = 6). Pre-1991 years are shown for context but
          excluded from thresholds, matching the framework's
          "driest years since 1991" baseline.
        - **Return period:** Weibull plotting position — RP =
          (n + 1)/rank of the 2026 value among 1991–2025 + 2026.
        - **ERA5 vs CHIRPS bias:** ERA5 runs substantially drier than
          CHIRPS over this zone in absolute terms; all comparisons here
          are within-dataset percentiles, which are insensitive to a
          constant bias but not to trend or variance differences.
        - **The real indicator is ENACTS.** ENACTS merges DMN station
          data with satellite estimates and is the authoritative input;
          this page only brackets the likely outcome. The 15 % threshold
          is the current app default; the endorsed 2024 PDF uses 35 % —
          both are shown.
        - Data prepared by `exploration/jun_jul_rainfall_make_data.py`
          (run 2026-08-24); series also on blob at
          `ds-aa-ner-drought/processed/rainfall/`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
