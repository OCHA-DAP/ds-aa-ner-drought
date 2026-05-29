import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def imports():
    import calendar

    import jinja2  # noqa: F401 — required by pandas.style in Pyodide
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    COLS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

    return COLS, calendar, mo, np, pd, plt


@app.cell
def load_data(mo, pd):
    import importlib
    import sys

    with mo.status.spinner(subtitle="Loading data..."):
        if sys.platform == "emscripten":
            import io
            import urllib.request

            _url = str(mo.notebook_location() / "public" / "iri_data.csv")
            with urllib.request.urlopen(_url) as _resp:
                df_iri = pd.read_csv(io.StringIO(_resp.read().decode("utf-8")))
        else:
            _stratus = importlib.import_module("ocha_stratus")
            blob_name = "ds-aa-ner-drought/raw/iri/ner_maproom_export_2026-04-25_thresh35 - Sheet1.csv"
            df_iri = _stratus.load_csv_from_blob(blob_name)

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
    df_iri["year"] = df_iri["year"].astype(int)
    _month_cols = [
        c for c in df_iri.columns if c not in ("year", "Aug", "JAS_SPI")
    ]
    df_iri[_month_cols] = df_iri[_month_cols] / 100.0
    df_iri = df_iri.sort_values("year").reset_index(drop=True)
    return (df_iri,)


@app.cell
def params(mo):
    ref_window = 10
    start_eval_year = (
        1998  # RP calc starts here; ref window may be <10 yrs for 1998–2000
    )
    end_eval_year = 2025
    pct_steps = list(
        range(0, 105, 5)
    )  # fraction triggering from top: 0%, 5%, ..., 100%
    mos = [1, 2, 3, 4, 5, 6]
    rp_target = 3.5
    mo.md(
        f"Evaluation years: **{start_eval_year}–{end_eval_year}** "
        f"({end_eval_year - start_eval_year + 1} years), "
        f"reference window: **{ref_window} years** (truncated for {start_eval_year}–{start_eval_year + 2}), "
        f"target RP: **{rp_target}**"
    )
    return (
        end_eval_year,
        mos,
        pct_steps,
        ref_window,
        rp_target,
        start_eval_year,
    )


@app.cell
def obs_ui(mo):
    obs_pct_slider = mo.ui.slider(
        start=5,
        stop=50,
        step=5,
        value=20,
        label="Obs arm: Aug percentile threshold",
        show_value=True,
    )
    mo.md(f"**Observational threshold:** {obs_pct_slider}")
    return (obs_pct_slider,)


@app.cell
def compute_forecast_triggers(
    COLS,
    calendar,
    df_iri,
    end_eval_year,
    mos,
    np,
    pd,
    pct_steps,
    ref_window,
    start_eval_year,
):
    """Forecast arm only — does not depend on obs_pct so slider won't rerun this."""
    _eval_years = list(range(start_eval_year, end_eval_year + 1))
    _consec_pairs = [(mos[i], mos[i + 1]) for i in range(len(mos) - 1)]

    _result_rows = []
    _thresh_rows = []

    for _pct in pct_steps:
        for _year in _eval_years:
            _ref = df_iri[
                df_iri["year"].between(_year - ref_window, _year - 1)
            ]
            _actual = df_iri[df_iri["year"] == _year].iloc[0]

            _trig_month = {}
            for _col in COLS:
                # threshold at (100 - pct)th percentile; pct = top-fraction that triggers
                _thresh = float(np.percentile(_ref[_col].values, 100 - _pct))
                _act_val = float(_actual[_col])
                _trig = _act_val >= _thresh
                _trig_month[_col] = _trig
                _thresh_rows.append(
                    {
                        "pct": _pct,
                        "year": _year,
                        "month": _col,
                        "threshold": _thresh,
                        "actual": _act_val,
                        "triggered": _trig,
                    }
                )

            _pair_trigs = {
                f"trig_{calendar.month_abbr[_m1]}_{calendar.month_abbr[_m2]}": (
                    _trig_month[calendar.month_abbr[_m1]]
                    and _trig_month[calendar.month_abbr[_m2]]
                )
                for _m1, _m2 in _consec_pairs
            }
            _trig_fcast = any(_pair_trigs.values())
            _result_rows.append(
                {
                    "pct": _pct,
                    "year": _year,
                    "trig_fcast": _trig_fcast,
                    **{f"trig_{_col}": _trig_month[_col] for _col in COLS},
                    **_pair_trigs,
                }
            )

    df_forecast = pd.DataFrame(_result_rows)
    df_thresholds = pd.DataFrame(_thresh_rows)
    return df_forecast, df_thresholds


@app.cell
def compute_obs_triggers(
    df_iri, end_eval_year, np, obs_pct_slider, pd, start_eval_year
):
    _obs_pct = obs_pct_slider.value
    _eval_years = list(range(start_eval_year, end_eval_year + 1))
    _obs_thresh = float(np.percentile(df_iri["Aug"].values, _obs_pct))
    _obs_rows = []
    for _year in _eval_years:
        _actual = df_iri[df_iri["year"] == _year].iloc[0]
        _act_aug = float(_actual["Aug"])
        _trig_obsv = _act_aug <= _obs_thresh
        _obs_rows.append(
            {
                "year": _year,
                "obs_threshold": _obs_thresh,
                "actual_aug": _act_aug,
                "trig_obsv": _trig_obsv,
            }
        )
    df_obs = pd.DataFrame(_obs_rows).set_index("year")
    return (df_obs,)


@app.cell
def combine_results(df_forecast, df_obs, pd, pct_steps):
    _obs = df_obs[["trig_obsv"]]
    _chunks = []
    for _pct in pct_steps:
        _fc = df_forecast[df_forecast["pct"] == _pct].set_index("year")
        _merged = _fc.join(_obs)
        _merged["trig_either"] = _merged["trig_fcast"] | _merged["trig_obsv"]
        _chunks.append(_merged.reset_index())
    df_results = pd.concat(_chunks, ignore_index=True)
    return (df_results,)


@app.cell
def trigger_summary(
    df_results,
    end_eval_year,
    mo,
    obs_pct_slider,
    pd,
    rp_target,
    start_eval_year,
):
    _obs_pct = obs_pct_slider.value
    _n_years = end_eval_year - start_eval_year + 1
    _rows = []
    for _pct, _grp in df_results.groupby("pct"):
        _n_fcast = int(_grp["trig_fcast"].sum())
        _n_obsv = int(_grp["trig_obsv"].sum())
        _n_either = int(_grp["trig_either"].sum())
        _rp_fcast = (
            round((_n_years + 1) / _n_fcast, 1)
            if _n_fcast > 0
            else float("inf")
        )
        _rp_obsv = (
            round((_n_years + 1) / _n_obsv, 1) if _n_obsv > 0 else float("inf")
        )
        _rp_either = (
            round((_n_years + 1) / _n_either, 1)
            if _n_either > 0
            else float("inf")
        )
        _rows.append(
            {
                "pct_triggering": _pct,
                "n_fcast": _n_fcast,
                "rp_fcast": _rp_fcast,
                f"n_obsv (Aug≤{_obs_pct}%)": _n_obsv,
                f"rp_obsv (Aug≤{_obs_pct}%)": _rp_obsv,
                "n_either": _n_either,
                "rp_either": _rp_either,
            }
        )
    df_summary = pd.DataFrame(_rows)

    _near_target = df_summary[
        df_summary["rp_either"].apply(
            lambda x: isinstance(x, float) and abs(x - rp_target) <= 0.6
        )
    ]
    _note = (
        f"Rows closest to target RP {rp_target}: pct = {_near_target['pct_triggering'].tolist()}"
        if len(_near_target)
        else f"No rows within 0.6 of target RP {rp_target}"
    )
    mo.vstack(
        [
            mo.md(
                f"### Trigger counts by percentile threshold\n\n"
                f"Obs arm (Aug) fixed at bottom **{_obs_pct}%** of full record. {_note}"
            ),
            mo.ui.table(df_summary),
        ]
    )
    return (df_summary,)


@app.cell
def find_closest_pct(df_summary, rp_target):
    _finite = df_summary[df_summary["rp_either"] < float("inf")]
    closest_pct = int(
        _finite.iloc[
            (_finite["rp_either"] - rp_target).abs().argsort().iloc[0]
        ]["pct_triggering"]
    )
    return (closest_pct,)


@app.cell
def triggered_years_detail(
    closest_pct, df_results, mo, obs_pct_slider, rp_target
):
    _obs_pct = obs_pct_slider.value
    _grp = df_results[df_results["pct"] == closest_pct]
    _fcast_years = sorted(_grp[_grp["trig_fcast"]]["year"].tolist())
    _obsv_years = sorted(_grp[_grp["trig_obsv"]]["year"].tolist())
    _either_years = sorted(_grp[_grp["trig_either"]]["year"].tolist())
    mo.md(
        f"At **pct = {closest_pct}%** (closest to RP {rp_target}):  \n"
        f"Forecast arm: **{_fcast_years}**  \n"
        f"Obs arm (Aug ≤{_obs_pct}%): **{_obsv_years}**  \n"
        f"Combined: **{_either_years}**"
    )


@app.cell
def selector_ui(COLS, closest_pct, mo, pct_steps):
    month_sel = mo.ui.dropdown(options=COLS, value="Jan", label="Month")
    pct_sel = mo.ui.dropdown(
        options=pct_steps,
        value=closest_pct,
        label="% triggering from top",
    )
    mo.hstack([month_sel, pct_sel])
    return month_sel, pct_sel


@app.cell
def threshold_evolution_plot(
    df_thresholds, month_sel, plt, pct_sel, ref_window
):
    _month = month_sel.value
    _pct = pct_sel.value
    _df = df_thresholds[
        (df_thresholds["month"] == _month) & (df_thresholds["pct"] == _pct)
    ].sort_values("year")

    _fig, _ax = plt.subplots(figsize=(10, 4))
    _ax.plot(
        _df["year"],
        _df["threshold"],
        lw=1.8,
        color="steelblue",
        label=f"Rolling {ref_window}-yr threshold (top {_pct}%)",
    )
    _triggered = _df[_df["triggered"]]
    _not_triggered = _df[~_df["triggered"]]
    _ax.scatter(
        _triggered["year"],
        _triggered["actual"],
        color="crimson",
        zorder=5,
        s=70,
        label="Triggered",
    )
    _ax.scatter(
        _not_triggered["year"],
        _not_triggered["actual"],
        color="gray",
        zorder=4,
        s=45,
        alpha=0.7,
        label="Not triggered",
    )
    _ax.set_title(
        f"{_month} — rolling {ref_window}-yr threshold at top {_pct}%"
    )
    _ax.set_xlabel("Year")
    _ax.set_ylabel("IRI forecast probability")
    _ax.legend()
    _ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    _fig


@app.cell
def all_months_plot(COLS, df_thresholds, plt, pct_sel, ref_window):
    _pct = pct_sel.value
    _fig, _axes = plt.subplots(2, 3, figsize=(14, 7), sharey=False)

    for _col, _ax in zip(COLS, _axes.flat):
        _df = df_thresholds[
            (df_thresholds["month"] == _col) & (df_thresholds["pct"] == _pct)
        ].sort_values("year")
        _ax.plot(_df["year"], _df["threshold"], lw=1.5, color="steelblue")
        _trig = _df[_df["triggered"]]
        _no_trig = _df[~_df["triggered"]]
        _ax.scatter(
            _trig["year"], _trig["actual"], color="crimson", zorder=5, s=55
        )
        _ax.scatter(
            _no_trig["year"],
            _no_trig["actual"],
            color="gray",
            zorder=4,
            s=35,
            alpha=0.6,
        )
        _ax.set_title(_col)
        _ax.spines[["top", "right"]].set_visible(False)
        _ax.tick_params(labelsize=8)

    _fig.suptitle(
        f"Rolling {ref_window}-yr threshold at top {_pct}% — red = triggered",
        fontsize=12,
    )
    plt.tight_layout()
    _fig


@app.cell
def aug_obs_plot(df_obs, obs_pct_slider, plt):
    _obs_pct = obs_pct_slider.value
    _df = df_obs.reset_index().sort_values("year")
    _fig, _ax = plt.subplots(figsize=(10, 3.5))
    _ax.axhline(
        _df["obs_threshold"].iloc[0],
        lw=1.8,
        color="darkorange",
        label=f"Aug threshold (bottom {_obs_pct}% of full record)",
    )
    _trig = _df[_df["trig_obsv"]]
    _no_trig = _df[~_df["trig_obsv"]]
    _ax.scatter(
        _trig["year"],
        _trig["actual_aug"],
        color="crimson",
        zorder=5,
        s=70,
        label="Obs triggered",
    )
    _ax.scatter(
        _no_trig["year"],
        _no_trig["actual_aug"],
        color="gray",
        zorder=4,
        s=45,
        alpha=0.7,
        label="Not triggered",
    )
    _ax.set_title(
        f"Aug observation arm — full historical threshold at bottom {_obs_pct}%"
    )
    _ax.set_xlabel("Year")
    _ax.set_ylabel("Aug value")
    _ax.legend()
    _ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    _fig


@app.cell
def trigger_detail_table(COLS, calendar, df_results, mo, mos, pct_sel):
    _pct = pct_sel.value
    _df = (
        df_results[df_results["pct"] == _pct]
        .copy()
        .sort_values("year", ascending=False)
    )

    _month_cols = [f"trig_{c}" for c in COLS]
    _pair_cols = [
        f"trig_{calendar.month_abbr[mos[i]]}_{calendar.month_abbr[mos[i+1]]}"
        for i in range(len(mos) - 1)
    ]
    _rename = {
        **{f"trig_{c}": c for c in COLS},
        **{
            f"trig_{calendar.month_abbr[mos[i]]}_{calendar.month_abbr[mos[i+1]]}": (
                f"{calendar.month_abbr[mos[i]]}+{calendar.month_abbr[mos[i+1]]}"
            )
            for i in range(len(mos) - 1)
        },
        "trig_fcast": "Fcast",
        "trig_obsv": "Obs",
        "trig_either": "Either",
    }
    _display = (
        _df[
            ["year"]
            + _month_cols
            + _pair_cols
            + ["trig_fcast", "trig_obsv", "trig_either"]
        ]
        .rename(columns=_rename)
        .reset_index(drop=True)
    )
    _highlight_cols = [c for c in _display.columns if c != "year"]
    _styled = _display.style.map(
        lambda v: (
            "background-color: #ffaaaa; color: #7a0000; font-weight: bold"
            if v is True
            else ""
        ),
        subset=_highlight_cols,
    )
    mo.vstack(
        [
            mo.md(f"### Per-year trigger detail (pct = {_pct}%)"),
            mo.Html(_styled.to_html()),
        ]
    )


@app.cell
def correlation_plot(
    COLS, df_iri, df_results, df_thresholds, np, plt, pct_sel, start_eval_year
):
    def _corr(x, y):
        _mask = ~(np.isnan(x.astype(float)) | np.isnan(y.astype(float)))
        if _mask.sum() < 3:
            return float("nan")
        return float(
            np.corrcoef(x[_mask].astype(float), y[_mask].astype(float))[0, 1]
        )

    _pct = pct_sel.value
    _eval = df_iri[df_iri["year"] >= start_eval_year].sort_values("year")
    _jas = _eval["JAS_SPI"].values

    _df_trig = (
        df_results[df_results["pct"] == _pct]
        .sort_values("year")
        .set_index("year")
        .loc[_eval["year"].values]
    )

    # distance = actual - threshold: positive when triggered, removes rolling climatology
    _df_dist = (
        df_thresholds[df_thresholds["pct"] == _pct]
        .assign(distance=lambda d: d["actual"] - d["threshold"])
        .set_index(["year", "month"])["distance"]
        .unstack("month")[COLS]
        .loc[_eval["year"].values]
    )

    _raw_r = [_corr(_eval[c].values, _jas) for c in COLS]
    _dist_r = [_corr(_df_dist[c].values, _jas) for c in COLS]
    _bin_r = [_corr(_df_trig[f"trig_{c}"].values, _jas) for c in COLS]

    _x = np.arange(len(COLS))
    _w = 0.25
    _fig, _ax = plt.subplots(figsize=(10, 4))
    _ax.bar(
        _x - _w,
        _raw_r,
        _w,
        label="Raw IRI value",
        color="steelblue",
        alpha=0.85,
    )
    _ax.bar(
        _x,
        _dist_r,
        _w,
        label="Distance from threshold",
        color="seagreen",
        alpha=0.85,
    )
    _ax.bar(
        _x + _w,
        _bin_r,
        _w,
        label=f"Binary trigger (top {_pct}%)",
        color="crimson",
        alpha=0.85,
    )
    _ax.axhline(0, color="black", lw=0.8)
    _ax.set_xticks(_x)
    _ax.set_xticklabels(COLS)
    _ax.set_ylabel("Pearson r with JAS SPI")
    _ax.set_title(
        "Correlation with observed JAS rainfall (negative = drought signal)"
    )
    _ax.legend()
    _ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    _fig


if __name__ == "__main__":
    app.run()
