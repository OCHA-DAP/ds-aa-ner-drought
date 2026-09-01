"""Matplotlib figures for the 2026 drought-pockets page.

Each function returns a base64-encoded PNG (data URI payload) for embedding
in the static page. Text inside figures is kept language-neutral (place
names, numbers, and short labels that read in both EN and FR); full
explanations live in the page's bilingual captions.
"""

import base64
import io
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

D = Path(__file__).parent / "public" / "pockets"

# --- palettes (ColorBrewer, colorblind-safe sequential/diverging schemes)
RP_BINS = [1, 2, 5, 10, 20, 100]
RP_COLORS = ["#f5f5eb", "#fed98e", "#fe9929", "#d95f0e", "#993404"]
RP_LABELS = ["< 2", "2–5", "5–10", "10–20", "≥ 20"]

CONV_COLORS = ["#f2f2ed", "#fdd49e", "#fc8d59", "#d7301f", "#7f0000"]

SEV_COLORS = {
    1: "#cdfacd",
    2: "#fae61e",
    3: "#e67800",
    4: "#c80000",
    5: "#640000",
}

DIV_CMAP = "BrBG"  # dry brown <-> wet green, neutral midpoint

REGION_LABEL_XY = {
    "NE001": (9.2, 19.6),  # Agadez
    "NE002": (12.6, 15.2),  # Diffa
    "NE003": (3.3, 12.65),  # Dosso
    "NE004": (7.1, 14.35),  # Maradi
    "NE005": (5.2, 15.55),  # Tahoua
    "NE006": (2.0, 14.35),  # Tillabéri
    "NE007": (9.3, 15.0),  # Zinder
}


def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=140, bbox_inches="tight", facecolor="white"
    )
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _load_admins():
    adm1 = gpd.read_file(D / "ner_adm1.gpkg")
    adm2 = gpd.read_file(D / "ner_adm2.gpkg")
    return adm1, adm2


def _basemap(ax, adm1):
    adm1.boundary.plot(ax=ax, color="#666666", linewidth=0.7, zorder=4)
    for pcode, (x, y) in REGION_LABEL_XY.items():
        name = adm1.loc[adm1["ADM1_PCODE"] == pcode, "ADM1_FR"].iloc[0]
        ax.annotate(
            name,
            (x, y),
            ha="center",
            fontsize=8,
            color="#333333",
            zorder=6,
            path_effects=[
                matplotlib.patheffects.withStroke(
                    linewidth=2.2, foreground="white"
                )
            ],
        )
    ax.set_axis_off()
    ax.set_aspect("equal")


def _rp_class(v):
    if pd.isna(v):
        return None
    return int(np.digitize(v, RP_BINS[1:-1]))


def rp_choropleth(ax, adm1, adm2, rp_by_pcode, hatch_pcodes=None):
    """Fill adm2 polygons by RP class; optional hatched overlay set."""
    g = adm2.merge(
        rp_by_pcode.rename("rp"),
        left_on="ADM2_PCODE",
        right_index=True,
        how="left",
    )
    g["cls"] = g["rp"].map(_rp_class)
    for cls, color in enumerate(RP_COLORS):
        sub = g[g["cls"] == cls]
        if len(sub):
            sub.plot(
                ax=ax,
                color=color,
                edgecolor="#ffffff",
                linewidth=0.4,
                zorder=2,
            )
    missing = g[g["cls"].isna()]
    if len(missing):
        missing.plot(
            ax=ax,
            color="#e9e9e9",
            edgecolor="#ffffff",
            linewidth=0.4,
            zorder=2,
        )
    if hatch_pcodes:
        sel = g[g["ADM2_PCODE"].isin(hatch_pcodes)]
        if len(sel):
            sel.plot(
                ax=ax,
                facecolor="none",
                edgecolor="#1a1a1a",
                hatch="///",
                linewidth=1.0,
                zorder=5,
            )
    _basemap(ax, adm1)


def rp_legend_handles():
    hs = [
        Patch(facecolor=c, edgecolor="#cccccc", label=l)
        for c, l in zip(RP_COLORS, RP_LABELS)
    ]
    return hs


def fig_convergence(summary, title_note=""):
    adm1, adm2 = _load_admins()
    g = adm2.merge(
        summary[["pcode", "conv_n", "final_severity"]],
        left_on="ADM2_PCODE",
        right_on="pcode",
        how="left",
    )
    fig, ax = plt.subplots(figsize=(9.2, 6.8))
    for k, color in enumerate(CONV_COLORS):
        sub = g[g["conv_n"] == k]
        if len(sub):
            sub.plot(
                ax=ax,
                color=color,
                edgecolor="#ffffff",
                linewidth=0.5,
                zorder=2,
            )
    sev4 = g[g["final_severity"] >= 4]
    if len(sev4):
        sev4.plot(
            ax=ax,
            facecolor="none",
            edgecolor="#1a1a1a",
            hatch="///",
            linewidth=1.2,
            zorder=5,
        )
    _basemap(ax, adm1)
    handles = [
        Patch(facecolor=c, edgecolor="#cccccc", label=str(k))
        for k, c in enumerate(CONV_COLORS)
    ] + [
        Patch(
            facecolor="none", edgecolor="#1a1a1a", hatch="///", label="HNRP 4"
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower left",
        fontsize=8,
        ncol=6,
        frameon=False,
        bbox_to_anchor=(0.0, -0.02),
        title=title_note,
        title_fontsize=8,
    )
    return _b64(fig)


def fig_pixel_percentile(mask_min_climo=40.0):
    adm1, _ = _load_admins()
    z = np.load(D / "chirps_junjul_stack.npz")
    years = z["years"]
    stack = np.stack([z[f"y{y}"] for y in years])
    cur = stack[years == 2026][0]
    hist = stack[years < 2026]
    with np.errstate(invalid="ignore"):
        pct = (
            100.0
            * (hist < cur[None]).sum(axis=0)
            / np.isfinite(hist).sum(axis=0)
        )
        climo = np.nanmean(hist, axis=0)
    pct = np.where(np.isfinite(cur) & (climo >= mask_min_climo), pct, np.nan)
    pct = np.where(z["admin_idx"] >= 0, pct, np.nan)  # Niger only

    fig, ax = plt.subplots(figsize=(9.2, 6.8))
    cmap = plt.get_cmap(DIV_CMAP, 10)
    im = ax.pcolormesh(
        z["lons"],
        z["lats"],
        pct,
        cmap=cmap,
        vmin=0,
        vmax=100,
        shading="auto",
        zorder=1,
    )
    _basemap(ax, adm1)
    ax.set_xlim(z["lons"].min(), z["lons"].max())
    ax.set_ylim(z["lats"].min(), z["lats"].max())
    cbar = fig.colorbar(
        im,
        ax=ax,
        orientation="horizontal",
        fraction=0.05,
        pad=0.02,
        aspect=45,
    )
    cbar.set_ticks([0, 10, 25, 50, 75, 90, 100])
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label("Percentile 1981–2025", fontsize=9)
    return _b64(fig)


def fig_rain_rp_pair(summary):
    adm1, adm2 = _load_admins()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))
    s = summary.set_index("pcode")
    rp_choropleth(axes[0], adm1, adm2, s["chirps_rp"])
    axes[0].set_title("CHIRPS · jun–jul", fontsize=11)
    rp_choropleth(axes[1], adm1, adm2, s["imerg_rp"])
    axes[1].set_title("IMERG · jun–août/aug", fontsize=11)
    fig.legend(
        handles=rp_legend_handles(),
        loc="lower center",
        fontsize=8,
        ncol=5,
        frameon=False,
        title="RP",
        title_fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return _b64(fig)


def fig_gauge_map(gauges):
    adm1, _ = _load_admins()
    fig, ax = plt.subplots(figsize=(9.2, 6.4))
    adm1.plot(ax=ax, color="#f7f7f2", edgecolor="#bbbbbb", linewidth=0.5)
    _basemap(ax, adm1)
    g = gauges.dropna(subset=["lat", "lon"])
    for _, r in g.iterrows():
        cls = _rp_class(r["rp"])
        color = "#e9e9e9" if cls is None else RP_COLORS[cls]
        ax.scatter(
            r["lon"],
            r["lat"],
            s=170,
            color=color,
            edgecolor="#333333",
            linewidth=0.8,
            zorder=6,
        )
        mm = (
            "excl."
            if pd.isna(r["junjul_2026_mm"])
            else f"{r['junjul_2026_mm']:.0f} mm"
        )
        ax.annotate(
            f"{r['name']}\n{mm}",
            (r["lon"], r["lat"]),
            textcoords="offset points",
            xytext=(0, 11),
            ha="center",
            fontsize=7,
            color="#1a1a1a",
            zorder=7,
            path_effects=[
                matplotlib.patheffects.withStroke(
                    linewidth=2, foreground="white"
                )
            ],
        )
    ax.legend(
        handles=rp_legend_handles(),
        loc="lower left",
        fontsize=8,
        ncol=5,
        frameon=False,
        title="RP jun–jul",
        title_fontsize=8,
    )
    ax.set_ylim(11.3, 19.2)
    return _b64(fig)


def fig_veg_strips(asi_hist, vhi_hist):
    """Per-region strip plots: grey = same-dekad history, red = 2026."""
    regions = [
        "Tillaberi",
        "Niamey",
        "Dosso",
        "Tahoua",
        "Maradi",
        "Zinder",
        "Diffa",
        "Agadez",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
    for ax, hist, label, worse_high in (
        (axes[0], asi_hist, "ASI (%)", True),
        (axes[1], vhi_hist, "VHI", False),
    ):
        for i, reg in enumerate(regions):
            s = hist[hist["region"] == reg].set_index("year")["v"]
            past = s[s.index < 2026]
            ax.scatter(
                past.values,
                [i] * len(past),
                color="#c4c4bd",
                s=22,
                zorder=2,
            )
            if 2026 in s.index:
                ax.scatter(
                    s.loc[2026],
                    i,
                    color="#d7301f",
                    s=95,
                    zorder=4,
                    edgecolor="#7f1d12",
                    linewidth=0.8,
                )
        ax.set_yticks(range(len(regions)))
        ax.set_yticklabels(regions, fontsize=9)
        ax.set_xlabel(label, fontsize=9)
        ax.grid(axis="x", color="#eeeeee", linewidth=0.7)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(labelsize=8, left=False)
        ax.invert_yaxis()
    handles = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            color="#c4c4bd",
            label="1984–2025",
        ),
        Line2D(
            [], [], marker="o", linestyle="", color="#d7301f", label="2026"
        ),
    ]
    axes[0].legend(
        handles=handles, fontsize=8, frameon=False, loc="lower right"
    )
    fig.tight_layout()
    return _b64(fig)


def fig_seas5_pair(summary):
    adm1, adm2 = _load_admins()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))
    s = summary.set_index("pcode")
    rp_choropleth(axes[0], adm1, adm2, s["seas5_jas_rp"])
    axes[0].set_title("JAS (jul obs + août/aug–sep SEAS5)", fontsize=10)
    rp_choropleth(axes[1], adm1, adm2, s["seas5_aso_rp"])
    axes[1].set_title("ASO (SEAS5)", fontsize=10)
    fig.legend(
        handles=rp_legend_handles(),
        loc="lower center",
        fontsize=8,
        ncol=5,
        frameon=False,
        title="RP",
        title_fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return _b64(fig)


def fig_hnrp(summary):
    adm1, adm2 = _load_admins()
    g = adm2.merge(
        summary[["pcode", "final_severity"]],
        left_on="ADM2_PCODE",
        right_on="pcode",
        how="left",
    )
    fig, ax = plt.subplots(figsize=(9.2, 6.4))
    for sev, color in SEV_COLORS.items():
        sub = g[g["final_severity"] == sev]
        if len(sub):
            sub.plot(
                ax=ax,
                color=color,
                edgecolor="#ffffff",
                linewidth=0.5,
                zorder=2,
            )
    _basemap(ax, adm1)
    handles = [
        Patch(facecolor=c, edgecolor="#cccccc", label=str(s))
        for s, c in SEV_COLORS.items()
        if (g["final_severity"] == s).any()
    ]
    ax.legend(
        handles=handles,
        loc="lower left",
        fontsize=8,
        ncol=5,
        frameon=False,
        title="JIAF",
        title_fontsize=8,
    )
    return _b64(fig)
