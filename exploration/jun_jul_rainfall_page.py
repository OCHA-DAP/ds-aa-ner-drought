"""Render the static 2026 Jun-Jul rainfall monitoring page.

Reads the data prepared by ``jun_jul_rainfall_make_data.py`` (plus the
bundled Maproom export ``iri_data.csv``) and writes a fully self-contained
``docs/rainfall/index.html`` — figures embedded as base64 PNGs, tables as
plain HTML. No marimo involved.

Usage: ``uv run python exploration/jun_jul_rainfall_page.py``
"""

import base64
import datetime
import io
from math import ceil
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PUBLIC_DIR = Path(__file__).parent / "public"
OUT_PATH = Path(__file__).parent.parent / "docs" / "rainfall" / "index.html"

PCT_DEFAULT = 15
PCT_ENDORSED = 35
BASELINE_START = 1991
BASELINE_END = 2025
CURRENT_YEAR = 2026
SOURCES = ["era5", "chirps"]
SOURCE_LABELS = {"era5": "ERA5", "chirps": "CHIRPS v2.0"}


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


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def load_data():
    df_rain = pd.read_csv(PUBLIC_DIR / "junjul_rainfall.csv")
    grids = np.load(PUBLIC_DIR / "junjul_rainfall_grids_2026.npz")
    df_iri = pd.read_csv(PUBLIC_DIR / "iri_data.csv")
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
    return df_rain, grids, df_iri


def compute_stats(df_rain):
    rows = []
    records = {}
    for src in SOURCES:
        df = df_rain[df_rain["source"] == src].set_index("year")
        record = df.loc[BASELINE_START:BASELINE_END, "seasonal_mm"]
        val26 = float(df.loc[CURRENT_YEAR, "seasonal_mm"])
        records[src] = (record, val26)

        thr15, _ = locked_threshold(record, PCT_DEFAULT)
        thr35, _ = locked_threshold(record, PCT_ENDORSED)
        rank, n_all = dry_rank(record.values, val26)
        rows.append(
            {
                "source": src,
                "record_median": record.median(),
                "value_2026": val26,
                "dry_rank_2026": rank,
                "n_ranked": n_all,
                "pctile_2026": 100 * rank / (n_all + 1),
                "rp_2026": (n_all + 1) / rank,
                "thresh_15": thr15,
                "trigger_15": val26 <= thr15,
                "margin_15": val26 - thr15,
                "thresh_35": thr35,
                "trigger_35": val26 <= thr35,
            }
        )
    return pd.DataFrame(rows).set_index("source"), records


def make_maps_figure(grids):
    adm0 = grids["adm0_boundary"]
    mask = grids["mask_boundary"]

    fig, axes = plt.subplots(
        len(SOURCES), 2, figsize=(13, 4.2 * len(SOURCES)), dpi=110
    )
    for i, src in enumerate(SOURCES):
        lons = grids[f"{src}_lons"]
        lats = grids[f"{src}_lats"]
        total = grids[f"{src}_total_2026"]
        climo = grids[f"{src}_climo"]
        with np.errstate(divide="ignore", invalid="ignore"):
            pct = np.where(climo > 5, 100 * total / climo, np.nan)

        ax = axes[i, 0]
        pm = ax.pcolormesh(
            lons,
            lats,
            total,
            cmap="YlGnBu",
            vmin=0,
            vmax=400,
            shading="nearest",
        )
        plt.colorbar(pm, ax=ax, label="mm", shrink=0.85)
        ax.set_title(
            f"{SOURCE_LABELS[src]} — Jun–Jul 2026 total (mm)", fontsize=11
        )

        ax2 = axes[i, 1]
        norm = mcolors.TwoSlopeNorm(vmin=0, vcenter=100, vmax=200)
        pm2 = ax2.pcolormesh(
            lons,
            lats,
            np.clip(pct, 0, 200),
            cmap="BrBG",
            norm=norm,
            shading="nearest",
        )
        plt.colorbar(pm2, ax=ax2, label="% of 1991–2020 normal", shrink=0.85)
        ax2.set_title(
            f"{SOURCE_LABELS[src]} — % of Jun–Jul normal", fontsize=11
        )

        for ax_ in (ax, ax2):
            ax_.plot(adm0[:, 0], adm0[:, 1], color="grey", lw=0.8)
            ax_.plot(mask[:, 0], mask[:, 1], color="black", lw=1.2)
            ax_.axhline(17, color="black", ls="--", lw=0.8)
            ax_.set_xlim(-0.5, 16.5)
            ax_.set_ylim(11.2, 18.2)
            ax_.set_aspect("equal")
            ax_.set_xlabel("lon")
            ax_.set_ylabel("lat")
    fig.tight_layout()
    return fig


def make_series_figure(df_rain, df_stats):
    fig, axes = plt.subplots(
        len(SOURCES),
        1,
        figsize=(11, 3.6 * len(SOURCES)),
        dpi=110,
        sharex=True,
    )
    for i, src in enumerate(SOURCES):
        ax = axes[i]
        df = df_rain[df_rain["source"] == src]
        hist = df[df["year"] < CURRENT_YEAR]
        cur = df[df["year"] == CURRENT_YEAR]
        s = df_stats.loc[src]

        ax.plot(
            hist["year"],
            hist["seasonal_mm"],
            "-o",
            ms=3.5,
            lw=1,
            color="steelblue",
        )
        ax.plot(
            cur["year"],
            cur["seasonal_mm"],
            "D",
            ms=8,
            color="crimson",
            zorder=5,
            label=f"2026: {s['value_2026']:.0f} mm",
        )
        ax.axhline(
            s["thresh_15"],
            color="crimson",
            lw=1.2,
            label=f"15% threshold: {s['thresh_15']:.0f} mm",
        )
        ax.axhline(
            s["thresh_35"],
            color="orange",
            lw=1,
            ls="--",
            label=f"35% threshold: {s['thresh_35']:.0f} mm",
        )
        base = hist[
            (hist["year"] >= BASELINE_START) & (hist["year"] <= BASELINE_END)
        ]
        below = base[base["seasonal_mm"] <= s["thresh_15"]]
        ax.plot(
            below["year"],
            below["seasonal_mm"],
            "o",
            ms=9,
            mfc="none",
            mec="crimson",
        )
        ax.axvspan(
            df["year"].min() - 0.5,
            BASELINE_START - 0.5,
            color="grey",
            alpha=0.12,
        )
        ax.set_title(
            f"{SOURCE_LABELS[src]} — Jun–Jul zonal-mean rainfall,"
            " Niger < 17°N",
            fontsize=11,
        )
        ax.set_ylabel("mm")
        ax.legend(loc="upper left", fontsize=8)
    axes[-1].set_xlabel(
        "year (grey band = pre-1991, outside the threshold record)"
    )
    fig.tight_layout()
    return fig


def make_spi_figure_and_stats(df_rain, df_iri, records):
    spi_thresh, _ = locked_threshold(df_iri["Aug"], PCT_DEFAULT)

    fig, axes = plt.subplots(1, len(SOURCES), figsize=(11, 4.4), dpi=110)
    spi_rows = []
    implied = {}
    for i, src in enumerate(SOURCES):
        ax = axes[i]
        df = df_rain[df_rain["source"] == src][["year", "seasonal_mm"]]
        m = df.merge(df_iri, on="year")
        m = m[(m["year"] >= BASELINE_START) & (m["year"] <= BASELINE_END)]
        pearson = float(np.corrcoef(m["seasonal_mm"], m["Aug"])[0, 1])
        spearman = float(
            m[["seasonal_mm", "Aug"]].corr(method="spearman").iloc[0, 1]
        )
        b, a = np.polyfit(m["seasonal_mm"], m["Aug"], 1)
        _, val26 = records[src]
        spi26 = b * val26 + a
        implied[src] = spi26
        spi_rows.append(
            {
                "Source": SOURCE_LABELS[src],
                "Pearson r": f"{pearson:.2f}",
                "Spearman ρ": f"{spearman:.2f}",
                "Implied 2026 SPI": f"{spi26:.3f}",
                "SPI 15% threshold": f"{spi_thresh:.3f}",
                "Implied trigger?": "YES" if spi26 <= spi_thresh else "no",
            }
        )

        ax.scatter(m["seasonal_mm"], m["Aug"], s=18, color="steelblue")
        xs = np.linspace(m["seasonal_mm"].min(), m["seasonal_mm"].max(), 2)
        ax.plot(xs, b * xs + a, color="grey", lw=1)
        ax.axhline(spi_thresh, color="crimson", lw=1)
        ax.axvline(val26, color="crimson", ls="--", lw=1)
        ax.plot(val26, spi26, "D", color="crimson", ms=8, zorder=5)
        ax.set_title(
            f"{SOURCE_LABELS[src]} vs Maproom SPI (r={pearson:.2f})",
            fontsize=11,
        )
        ax.set_xlabel(f"{SOURCE_LABELS[src]} Jun–Jul rainfall (mm)")
        ax.set_ylabel("Maproom Jun–Jul SPI")
    fig.tight_layout()
    return fig, pd.DataFrame(spi_rows), implied, spi_thresh


def html_table(df):
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    body = ""
    for _, row in df.iterrows():
        cells = "".join(
            f'<td class="{"yes" if v == "YES" else ""}">{v}</td>' for v in row
        )
        body += f"<tr>{cells}</tr>\n"
    return (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def build_summary_table(df_stats):
    rows = []
    for src, s in df_stats.iterrows():
        rows.append(
            {
                "Source": SOURCE_LABELS[src],
                "2026 Jun–Jul (mm)": f"{s['value_2026']:.0f}",
                "Record median (mm)": f"{s['record_median']:.0f}",
                "Dry rank of 2026": (
                    f"{int(s['dry_rank_2026'])} of {int(s['n_ranked'])}"
                ),
                "Empirical percentile": f"{s['pctile_2026']:.0f}%",
                "RP of 2026 dryness": f"{s['rp_2026']:.1f} yr",
                "15% threshold (mm)": f"{s['thresh_15']:.0f}",
                "Margin vs 15% (mm)": f"{s['margin_15']:+.0f}",
                "Triggers at 15%?": "YES" if s["trigger_15"] else "no",
                "Triggers at 35%?": "YES" if s["trigger_35"] else "no",
            }
        )
    return html_table(pd.DataFrame(rows))


def build_sweep_table(records):
    rows = []
    for pct in [5, 10, 15, 20, 25, 30, 35, 40]:
        row = {"Percentile": f"{pct}%"}
        for src in SOURCES:
            record, val26 = records[src]
            thr, _ = locked_threshold(record, pct)
            row[f"{SOURCE_LABELS[src]} threshold (mm)"] = f"{thr:.0f}"
            row[f"{SOURCE_LABELS[src]} 2026 triggers?"] = (
                "YES" if val26 <= thr else "no"
            )
        rows.append(row)
    return html_table(pd.DataFrame(rows))


def build_bottom_line(df_stats, implied, spi_thresh):
    parts = []
    for src, s in df_stats.iterrows():
        trig = (
            "<strong>would trigger</strong>"
            if s["trigger_15"]
            else "would <em>not</em> trigger"
        )
        parts.append(
            f"<li><strong>{SOURCE_LABELS[src]}</strong>: 2026 is the "
            f"{ordinal(int(s['dry_rank_2026']))} driest of "
            f"{int(s['n_ranked'])} years "
            f"(≈{s['pctile_2026']:.0f}th percentile, "
            f"1-in-{s['rp_2026']:.1f}-yr dryness), "
            f"{abs(s['margin_15']):.0f} mm "
            f"{'below' if s['margin_15'] <= 0 else 'above'} the "
            f"{PCT_DEFAULT}% threshold → {trig}. "
            f"Implied Maproom SPI ≈ {implied[src]:.3f} "
            f"(threshold {spi_thresh:.3f}).</li>"
        )
    return "\n".join(parts)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Niger 2026 Jun–Jul rainfall vs the observational trigger</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a; background: #ffffff;
    margin: 0; padding: 2rem 1rem 4rem;
    line-height: 1.55;
  }}
  main {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 1.7rem; margin-bottom: 0.3rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 2.4rem;
       border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; }}
  figure {{ margin: 1.2rem 0; text-align: center; }}
  figure img {{ max-width: 100%; height: auto; }}
  table {{ border-collapse: collapse; margin: 1rem 0; font-size: 0.88rem;
          width: 100%; }}
  th, td {{ border: 1px solid #d9d9d9; padding: 0.4rem 0.6rem;
           text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  td.yes {{ background: #fdecea; color: #b3261e; font-weight: 600; }}
  .callout {{ background: #fff8e6; border-left: 4px solid #e6a700;
             padding: 0.6rem 1rem; margin: 1rem 0; }}
  .note {{ color: #555; font-size: 0.85rem; font-style: italic; }}
  code {{ background: #f2f2f2; padding: 0.1rem 0.3rem; border-radius: 3px;
         font-size: 0.85em; }}
  footer {{ margin-top: 3rem; color: #777; font-size: 0.8rem; }}
  .overflow {{ overflow-x: auto; }}
</style>
</head>
<body>
<!-- back to the site landing page -->
<style>
  .home-link {{ display:inline-block; margin:10px 0 0 12px; padding:6px 12px;
    font:500 13px/1 system-ui,sans-serif; color:#1e795f;
    background:#e9f5f1; border:1px solid #d4eae4; border-radius:4px;
    text-decoration:none; }}
  .home-link:hover {{ background:#d4eae4; }}
</style>
<a class="home-link" href="../">&#8592; Niger drought AA</a>
<main>

<h1>Niger 2026 Jun–Jul rainfall vs the observational trigger</h1>

<p><strong>Question:</strong> how likely is the observational arm of the
Niger drought trigger to fire this year? The arm uses the <strong>ENACTS
MON Jun–Jul SPI</strong> published on the IRI Maproom, which is not yet
available to us for 2026. As a stopgap, this page evaluates 2026 Jun–Jul
rainfall over the monitored zone (<strong>Niger south of 17°N</strong>)
in two independent datasets we <em>do</em> have — <strong>ERA5</strong>
reanalysis and <strong>CHIRPS v2.0</strong> — and asks where 2026 falls
in each dataset's own historical record, relative to the current
candidate threshold (<strong>driest 15&thinsp;% of years</strong>, full
record, value-locked).</p>

<div class="callout">⚠️ This is a proxy analysis. The trigger decision is
made on the ENACTS SPI from the Maproom, not on either of these
datasets.</div>

<h2>2026 Jun–Jul rainfall over the monitored zone</h2>

<p>Left: total Jun–Jul precipitation. Right: the same total as a
percentage of the 1991–2020 Jun–Jul climatology. The monitored zone
(Niger south of 17°N, black outline) is the spatial mean used everywhere
below; the dashed line is 17°N.</p>

<figure><img src="data:image/png;base64,{maps_png}"
  alt="Maps of 2026 Jun-Jul rainfall totals and percent of normal for
  ERA5 and CHIRPS over Niger south of 17N"></figure>

<h2>Historical record and where 2026 falls</h2>

<p>Zonal-mean Jun–Jul rainfall by year. The red line is the
<strong>15&thinsp;%</strong> value-locked threshold over the 1991–2025
record; the lighter orange line is the endorsed PDF's
<strong>35&thinsp;%</strong> alternative. Years at or below the
15&thinsp;% threshold are circled.</p>

<figure><img src="data:image/png;base64,{series_png}"
  alt="Yearly Jun-Jul zonal-mean rainfall for ERA5 and CHIRPS with
  threshold lines and 2026 highlighted"></figure>

<h3>2026 vs the threshold — summary</h3>

<div class="overflow">{summary_table}</div>

<p class="note">Dry rank counts 2026 within the 1991–2025 record plus
2026 itself (1 = driest). The return period is the Weibull plotting
position (n+1)/rank of the 2026 value; percentile = rank/(n+1). A
positive margin means 2026 is wetter than the threshold (no
trigger).</p>

<h3>Sensitivity: would 2026 trigger at other percentile choices?</h3>

<div class="overflow">{sweep_table}</div>

<h2>Cross-check against the actual trigger indicator</h2>

<p>The trigger's observational indicator is the Maproom Jun–Jul SPI (the
"Aug" column of the trigger dataset, 1991–2025). If ERA5 or CHIRPS is to
stand in for it, they should co-vary with it. The scatter below shows
each proxy against the Maproom SPI over the common record, with a
least-squares fit used to translate the 2026 proxy value into an implied
2026 SPI.</p>

<figure><img src="data:image/png;base64,{spi_png}"
  alt="Scatter plots of ERA5 and CHIRPS Jun-Jul rainfall against the
  Maproom SPI with fits and the 2026 value marked"></figure>

<div class="overflow">{spi_table}</div>

<p class="note">Red solid line: the 15&thinsp;% value-locked threshold on
the SPI record itself; red dashed line and diamond: the 2026 proxy value
and its implied SPI. The implied SPI is a linear translation and carries
the fit's uncertainty — treat it as indicative only.</p>

<h2>Bottom line</h2>

<ul>
{bottom_line}
</ul>

<p>Both proxies put 2026 at or below the 15&thinsp;% rainfall threshold,
but CHIRPS — much the better-correlated proxy — sits <em>exactly at the
line</em>: 6th driest of 36 (the threshold rank), and its implied SPI
lands within a few thousandths of the SPI threshold. Read this as a
<strong>coin-flip-or-better chance</strong> that the ENACTS value
triggers at 15&thinsp;%, and a near-certain trigger if the endorsed
35&thinsp;% threshold is used instead.</p>

<h2>Methodology &amp; caveats</h2>

<ul>
<li><strong>Zone:</strong> Niger admin-0 (FieldMaps CODAB) clipped to
south of 17°N — the monitored zone of the Niger drought AA framework.
Statistic: unweighted pixel mean over the zone.</li>
<li><strong>ERA5:</strong> monthly total-precipitation COGs from the
team raster pipeline (prod blob, <code>era5/monthly/processed/</code>),
mm/day × days-in-month. 1981–2026.</li>
<li><strong>CHIRPS v2.0:</strong> Africa monthly GeoTIFFs from the
Climate Hazards Center (final product, mm/month). 1981–2026.</li>
<li><strong>Threshold convention:</strong> value-locked, as in the
trigger explorer — the <em>k</em>-th driest observed year where
<em>k&nbsp;=&nbsp;ceil(p/100&nbsp;×&nbsp;n)</em> over the 1991–2025
record (n&nbsp;=&nbsp;35; p&nbsp;=&nbsp;15&thinsp;% →
k&nbsp;=&nbsp;6). Pre-1991 years are shown for context but excluded
from thresholds, matching the framework's "driest years since 1991"
baseline.</li>
<li><strong>Return period:</strong> Weibull plotting position — RP =
(n&nbsp;+&nbsp;1)/rank of the 2026 value among 1991–2025 + 2026.</li>
<li><strong>ERA5 vs CHIRPS bias:</strong> ERA5 runs substantially drier
than CHIRPS over this zone in absolute terms; all comparisons here are
within-dataset percentiles, which are insensitive to a constant bias
but not to trend or variance differences.</li>
<li><strong>The real indicator is ENACTS.</strong> ENACTS merges DMN
station data with satellite estimates and is the authoritative input;
this page only brackets the likely outcome. The 15&thinsp;% threshold
is the current app default; the endorsed 2024 PDF uses 35&thinsp;% —
both are shown.</li>
<li>Data prepared by
<code>exploration/jun_jul_rainfall_make_data.py</code>; page rendered by
<code>exploration/jun_jul_rainfall_page.py</code>; series also on blob
at <code>ds-aa-ner-drought/processed/rainfall/</code>.</li>
</ul>

<footer>Generated {generated} · OCHA Centre for Humanitarian Data ·
<a href="../">trigger explorer</a></footer>

</main>
</body>
</html>
"""


def main():
    df_rain, grids, df_iri = load_data()
    df_stats, records = compute_stats(df_rain)

    maps_png = fig_to_b64(make_maps_figure(grids))
    series_png = fig_to_b64(make_series_figure(df_rain, df_stats))
    spi_fig, df_spi, implied, spi_thresh = make_spi_figure_and_stats(
        df_rain, df_iri, records
    )
    spi_png = fig_to_b64(spi_fig)

    html = PAGE_TEMPLATE.format(
        maps_png=maps_png,
        series_png=series_png,
        spi_png=spi_png,
        summary_table=build_summary_table(df_stats),
        sweep_table=build_sweep_table(records),
        spi_table=html_table(df_spi),
        bottom_line=build_bottom_line(df_stats, implied, spi_thresh),
        generated=datetime.date.today().isoformat(),
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
