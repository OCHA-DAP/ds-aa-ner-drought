import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def imports():
    import calendar

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
    obs_pct = 20  # bottom % of Aug reference that triggers obs arm (fixed)
    mos = [1, 2, 3, 4, 5, 6]
    rp_target = 3.5
    mo.md(
        f"Evaluation years: **{start_eval_year}–{end_eval_year}** "
        f"({end_eval_year - start_eval_year + 1} years), "
        f"reference window: **{ref_window} years** (truncated for {start_eval_year}–{start_eval_year + 2}), "
        f"obs arm: fixed threshold at bottom **{obs_pct}%** of full Aug record, "
        f"target RP: **{rp_target}**"
    )
    return (
        end_eval_year,
        mos,
        obs_pct,
        pct_steps,
        ref_window,
        rp_target,
        start_eval_year,
    )


@app.cell
def compute_triggers(
    COLS,
    calendar,
    df_iri,
    end_eval_year,
    mos,
    np,
    obs_pct,
    pd,
    pct_steps,
    ref_window,
    start_eval_year,
):
    _eval_years = list(range(start_eval_year, end_eval_year + 1))
    _consec_pairs = [(mos[i], mos[i + 1]) for i in range(len(mos) - 1)]

    # Pre-compute obs arm (Aug, bottom obs_pct%) — single fixed threshold from full record
    _obs_thresh = float(np.percentile(df_iri["Aug"].values, obs_pct))
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

            _trig_pairs = [
                _trig_month[calendar.month_abbr[_m1]]
                and _trig_month[calendar.month_abbr[_m2]]
                for _m1, _m2 in _consec_pairs
            ]
            _trig_fcast = any(_trig_pairs)
            _trig_obsv = bool(df_obs.loc[_year, "trig_obsv"])
            _result_rows.append(
                {
                    "pct": _pct,
                    "year": _year,
                    "trig_fcast": _trig_fcast,
                    "trig_obsv": _trig_obsv,
                    "trig_either": _trig_fcast or _trig_obsv,
                    **{f"trig_{_col}": _trig_month[_col] for _col in COLS},
                }
            )

    df_results = pd.DataFrame(_result_rows)
    df_thresholds = pd.DataFrame(_thresh_rows)
    return df_obs, df_results, df_thresholds


@app.cell
def trigger_summary(
    df_results, end_eval_year, mo, obs_pct, pd, rp_target, start_eval_year
):
    _n_years = end_eval_year - start_eval_year + 1
    _rows = []
    for _pct, _grp in df_results.groupby("pct"):
        _n_fcast = int(_grp["trig_fcast"].sum())
        _n_obsv = int(_grp["trig_obsv"].sum())
        _n_trig = int(_grp["trig_either"].sum())
        _rp = (_n_years + 1) / _n_trig if _n_trig > 0 else float("inf")
        _rows.append(
            {
                "pct_triggering": _pct,
                "n_fcast": _n_fcast,
                f"n_obsv (Aug ≤{obs_pct}%)": _n_obsv,
                "n_either": _n_trig,
                "return_period": (
                    round(_rp, 1) if _n_trig > 0 else float("inf")
                ),
            }
        )
    df_summary = pd.DataFrame(_rows)

    _near_target = df_summary[
        df_summary["return_period"].apply(
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
                f"### Trigger counts by percentile threshold\n\nObs arm (Aug) fixed at bottom {obs_pct}%. {_note}"
            ),
            mo.ui.table(df_summary),
        ]
    )
    return (df_summary,)


@app.cell
def find_closest_pct(df_summary, rp_target):
    _finite = df_summary[df_summary["return_period"] < float("inf")]
    closest_pct = int(
        _finite.iloc[
            (_finite["return_period"] - rp_target).abs().argsort().iloc[0]
        ]["pct_triggering"]
    )
    return (closest_pct,)


@app.cell
def triggered_years_detail(closest_pct, df_results, mo, obs_pct, rp_target):
    _grp = df_results[df_results["pct"] == closest_pct]
    _fcast_years = sorted(_grp[_grp["trig_fcast"]]["year"].tolist())
    _obsv_years = sorted(_grp[_grp["trig_obsv"]]["year"].tolist())
    _either_years = sorted(_grp[_grp["trig_either"]]["year"].tolist())
    mo.md(
        f"At **pct = {closest_pct}%** (closest to RP {rp_target}):  \n"
        f"Forecast arm: **{_fcast_years}**  \n"
        f"Obs arm (Aug ≤{obs_pct}%): **{_obsv_years}**  \n"
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
def aug_obs_plot(df_obs, obs_pct, plt):
    _df = df_obs.reset_index().sort_values("year")
    _fig, _ax = plt.subplots(figsize=(10, 3.5))
    _ax.axhline(
        _df["obs_threshold"].iloc[0],
        lw=1.8,
        color="darkorange",
        label=f"Aug threshold (bottom {obs_pct}% of full record)",
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
        f"Aug observation arm — full historical threshold at bottom {obs_pct}%"
    )
    _ax.set_xlabel("Year")
    _ax.set_ylabel("Aug value")
    _ax.legend()
    _ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    _fig


if __name__ == "__main__":
    app.run()
