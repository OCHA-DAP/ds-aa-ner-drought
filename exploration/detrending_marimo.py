import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def imports():
    import calendar

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import ocha_stratus as stratus
    import pandas as pd
    from scipy.stats import linregress, mannwhitneyu, spearmanr
    from statsmodels.othermod.betareg import BetaModel

    COLS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

    def squeeze(y, n):
        return (y * (n - 1) + 0.5) / n

    return (
        BetaModel,
        COLS,
        calendar,
        linregress,
        mannwhitneyu,
        mo,
        np,
        pd,
        plt,
        spearmanr,
        squeeze,
        stratus,
    )


@app.cell
def load_data(stratus):
    blob_name = "ds-aa-ner-drought/raw/iri/ner_maproom_export_2026-04-25_thresh35 - Sheet1.csv"
    df_stats_iri = stratus.load_csv_from_blob(blob_name)
    df_stats_iri.columns = [
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
    df_stats_iri["year"] = df_stats_iri["year"].astype(int)
    df_stats_iri = df_stats_iri.sort_values("year", ascending=False)
    _month_cols = [
        c for c in df_stats_iri.columns if c not in ("year", "Aug", "JAS_SPI")
    ]
    df_stats_iri[_month_cols] = df_stats_iri[_month_cols] / 100.0
    x_norm = df_stats_iri["year"].values - df_stats_iri["year"].values[0]
    years = df_stats_iri["year"].values
    return df_stats_iri, x_norm, years


@app.cell
def _detrend_header(mo):
    mo.md(
        """
    ## Detrending

        Three-step procedure: (1) fit a beta regression trend per month and divide
        out, (2) check for remaining variance trend, (3) scale residuals to remove
        heteroscedasticity. The result is a stationary series suitable for
        threshold-based trigger design.
    """
    )
    return


@app.cell
def beta_detrend(
    BetaModel,
    COLS,
    df_stats_iri,
    mo,
    np,
    squeeze,
    start_year,
    x_norm,
    years,
):
    # Full-record design matrix
    _n_all = len(x_norm)
    _X_all = np.column_stack([np.ones(_n_all), x_norm])

    # 1998+ subset
    _keep = df_stats_iri["year"].values >= start_year
    x_norm_fit = x_norm[_keep]
    years_fit = years[_keep]
    _n_fit = len(x_norm_fit)
    _X_fit = np.column_stack([np.ones(_n_fit), x_norm_fit])
    _df_fit = df_stats_iri[df_stats_iri["year"] >= start_year]

    df_detrended_beta_all_full = df_stats_iri[
        ["year"]
    ].copy()  # all years, full-record model
    df_detrended_beta_all = _df_fit[
        ["year"]
    ].copy()  # 1998+ only, full-record model
    df_detrended_beta_fit = _df_fit[["year"]].copy()  # 1998+ only, 1998+ model
    beta_results_all = {}
    beta_results_fit = {}

    _rows = []
    for _col in COLS:
        # Fit on full record
        _res_all = BetaModel(
            squeeze(df_stats_iri[_col].values, _n_all), _X_all
        ).fit(disp=False)
        beta_results_all[_col] = _res_all

        # Fit on 1998+ only
        _res_fit = BetaModel(
            squeeze(_df_fit[_col].values, _n_fit), _X_fit
        ).fit(disp=False)
        beta_results_fit[_col] = _res_fit

        _mean_all = _res_all.fittedvalues.mean()

        # Mean-detrend ALL years using full-record model (for variance fit input)
        df_detrended_beta_all_full[_col] = (
            df_stats_iri[_col].values / _res_all.fittedvalues
        ) * _mean_all

        # Mean-detrend 1998+ data using each model's trend at those years
        _y_fit = _df_fit[_col].values
        df_detrended_beta_all[_col] = (
            _y_fit / _res_all.predict(_X_fit)
        ) * _mean_all

        _trend_fit = _res_fit.fittedvalues
        df_detrended_beta_fit[_col] = (_y_fit / _trend_fit) * _trend_fit.mean()

        _rows.append(
            f"| {_col} | {_res_all.params[1]:.4f} | {_res_all.pvalues[1]:.3f} "
            f"| {_res_fit.params[1]:.4f} | {_res_fit.pvalues[1]:.3f} |"
        )

    _table = (
        "| Month | Full coef | Full p | 1998+ coef | 1998+ p |\n"
        "|---|---|---|---|---|\n" + "\n".join(_rows)
    )
    mo.md(f"### Beta regression — trend coefficients\n\n{_table}")
    return (
        beta_results_all,
        beta_results_fit,
        df_detrended_beta_all,
        df_detrended_beta_all_full,
        df_detrended_beta_fit,
        x_norm_fit,
        years_fit,
    )


@app.cell
def check_variance_trend(
    COLS,
    df_detrended_beta_all_full,
    df_detrended_beta_fit,
    mo,
    np,
    spearmanr,
    x_norm,
    x_norm_fit,
):
    _rows = []
    for _col in COLS:
        # Full-record model: check variance trend over all years
        _ra = df_detrended_beta_all_full[_col]
        _r_all, _p_all = spearmanr(x_norm, np.abs(_ra - _ra.mean()))
        # 1998+ model: check over 1998+ only
        _rf = df_detrended_beta_fit[_col]
        _r_fit, _p_fit = spearmanr(x_norm_fit, np.abs(_rf - _rf.mean()))
        _rows.append(
            f"| {_col} | {_r_all:.3f} | {_p_all:.3f} | {'⚠' if _p_all < 0.05 else 'ok'} "
            f"| {_r_fit:.3f} | {_p_fit:.3f} | {'⚠' if _p_fit < 0.05 else 'ok'} |"
        )
    _table = (
        "| Month | Full r | Full p | Full | 1998+ r | 1998+ p | 1998+ |\n"
        "|---|---|---|---|---|---|---|\n" + "\n".join(_rows)
    )
    mo.md(
        f"### Variance trend check (after mean detrend)\n\n"
        f"Spearman r between year and |residual|. ⚠ = heteroscedasticity present.\n\n"
        f"{_table}"
    )
    return


@app.cell
def full_detrend(
    COLS,
    df_detrended_beta_all,
    df_detrended_beta_all_full,
    df_detrended_beta_fit,
    linregress,
    np,
    x_norm,
    x_norm_fit,
):
    df_detrended_final_all = df_detrended_beta_all[["year"]].copy()
    df_detrended_final_fit = df_detrended_beta_fit[["year"]].copy()
    var_params_all = {}
    var_params_fit = {}

    for _col in COLS:
        # ── Full-record model: fit variance on ALL years, apply to 1998+ ──────
        _resid_all = df_detrended_beta_all_full[_col].values
        _resid_mean = _resid_all.mean()
        _abs_resid_all = np.abs(_resid_all - _resid_mean)
        _abs_resid_mean = _abs_resid_all.mean()
        _slope_v, _intercept_v, _r_v, _p_v, _ = linregress(
            x_norm, _abs_resid_all
        )
        _fitted_spread = np.clip(
            _intercept_v + _slope_v * x_norm_fit, 1e-3, None
        )
        _resid_1998 = df_detrended_beta_all[_col].values
        _resid_centered_1998 = _resid_1998 - _resid_mean
        df_detrended_final_all[_col] = (
            _resid_centered_1998 / _fitted_spread
        ) * _abs_resid_mean + _resid_mean
        var_params_all[_col] = {
            "resid_mean": _resid_mean,
            "abs_resid_mean": _abs_resid_mean,
            "slope_v": _slope_v,
            "intercept_v": _intercept_v,
            "pvalue_v": _p_v,
            "r2_v": _r_v**2,
        }

        # ── 1998+ model: fit and apply entirely on 1998+ ──────────────────────
        _resid_f = df_detrended_beta_fit[_col].values
        _resid_mean_f = _resid_f.mean()
        _resid_centered_f = _resid_f - _resid_mean_f
        _abs_resid_f = np.abs(_resid_centered_f)
        _abs_resid_mean_f = _abs_resid_f.mean()
        _slope_f, _intercept_f, _r_f, _p_f, _ = linregress(
            x_norm_fit, _abs_resid_f
        )
        _fitted_spread_f = np.clip(
            _intercept_f + _slope_f * x_norm_fit, 1e-3, None
        )
        df_detrended_final_fit[_col] = (
            _resid_centered_f / _fitted_spread_f
        ) * _abs_resid_mean_f + _resid_mean_f
        var_params_fit[_col] = {
            "resid_mean": _resid_mean_f,
            "abs_resid_mean": _abs_resid_mean_f,
            "slope_v": _slope_f,
            "intercept_v": _intercept_f,
            "pvalue_v": _p_f,
            "r2_v": _r_f**2,
        }
    return (
        df_detrended_final_all,
        df_detrended_final_fit,
        var_params_all,
        var_params_fit,
    )


@app.cell
def detrend_gof(
    COLS,
    beta_results_all,
    beta_results_fit,
    df_stats_iri,
    mo,
    np,
    squeeze,
    start_year,
    var_params_all,
    var_params_fit,
):
    _df_fit = df_stats_iri[df_stats_iri["year"] >= start_year]
    _n_all = len(df_stats_iri)
    _n_fit = len(_df_fit)

    _rows = []
    for _col in COLS:
        _res_all = beta_results_all[_col]
        _res_fit = beta_results_fit[_col]

        # Beta R²: Pearson r² between fitted trend and squeezed observations
        _y_sq_all = squeeze(df_stats_iri[_col].values, _n_all)
        _r2_b_all = float(
            np.corrcoef(_res_all.fittedvalues, _y_sq_all)[0, 1] ** 2
        )

        _y_sq_fit = squeeze(_df_fit[_col].values, _n_fit)
        _r2_b_fit = float(
            np.corrcoef(_res_fit.fittedvalues, _y_sq_fit)[0, 1] ** 2
        )

        _r2_v_all = var_params_all[_col]["r2_v"]
        _r2_v_fit = var_params_fit[_col]["r2_v"]

        _rows.append(
            f"| {_col} "
            f"| {_r2_b_all:.3f} | {_r2_v_all:.3f} "
            f"| {_r2_b_fit:.3f} | {_r2_v_fit:.3f} |"
        )

    _table = (
        "| Month | Full β R² | Full var R² | 1998+ β R² | 1998+ var R² |\n"
        "|---|---|---|---|---|\n" + "\n".join(_rows)
    )
    mo.md(
        "### Goodness of fit\n\n"
        "**β R²**: Pearson r² between the beta trend's fitted values and the "
        "squeezed observations — how well the mean-trend model fits the data.  \n"
        "**Var R²**: r² of the linear fit on |residual| vs year — how much of "
        "the heteroscedasticity is explained by a linear spread trend.\n\n"
        + _table
    )
    return


@app.cell
def detrend_steps_plot(
    COLS,
    beta_results_all,
    beta_results_fit,
    df_detrended_beta_all,
    df_detrended_beta_fit,
    df_detrended_final_all,
    df_detrended_final_fit,
    df_stats_iri,
    np,
    plt,
    var_params_all,
    var_params_fit,
    x_norm_fit,
    years_fit,
):
    _idx = np.argsort(years_fit)
    _years_asc = years_fit[_idx]
    _xnorm_asc = x_norm_fit[_idx]
    _X_asc = np.column_stack([np.ones(len(_years_asc)), _xnorm_asc])

    _c_all = "#4477AA"  # blue = full record
    _c_fit = "#EE6677"  # red  = 1998+
    _c_raw = "#AAAAAA"

    _fig, _axes = plt.subplots(len(COLS), 4, figsize=(18, 18), sharex=True)

    _col_titles = [
        "Raw + beta trend",
        "Mean-detrended",
        "|Residual| trend",
        "Fully detrended",
    ]
    for _j, _t in enumerate(_col_titles):
        _axes[0, _j].set_title(_t, fontsize=10, fontweight="bold")

    _df_raw = df_stats_iri[df_stats_iri["year"] >= years_fit.min()]

    for _i, _col in enumerate(COLS):
        _res_all = beta_results_all[_col]
        _res_fit = beta_results_fit[_col]
        _vp_all = var_params_all[_col]
        _vp_fit = var_params_fit[_col]

        _raw = _df_raw[_col].values[_idx]
        _mdet_all = df_detrended_beta_all[_col].values[_idx]
        _mdet_fit = df_detrended_beta_fit[_col].values[_idx]
        _fdet_all = df_detrended_final_all[_col].values[_idx]
        _fdet_fit = df_detrended_final_fit[_col].values[_idx]
        _trend_all = _res_all.predict(_X_asc)
        _trend_fit = _res_fit.fittedvalues[_idx]

        # Col 0: raw + both beta trends with p-values
        _ax = _axes[_i, 0]
        _ax.scatter(_years_asc, _raw, s=14, color=_c_raw, alpha=0.8, zorder=3)
        _ax.plot(
            _years_asc,
            _trend_all,
            color=_c_all,
            lw=2,
            label=f"Full  p={_res_all.pvalues[1]:.3f}",
        )
        _ax.plot(
            _years_asc,
            _trend_fit,
            color=_c_fit,
            lw=2,
            ls="--",
            label=f"1998+ p={_res_fit.pvalues[1]:.3f}",
        )
        _ax.set_ylabel(_col, fontsize=10)
        _ax.legend(fontsize=7, loc="upper right")

        # Col 1: mean-detrended (both)
        _ax = _axes[_i, 1]
        _ax.scatter(
            _years_asc, _mdet_all, s=14, color=_c_all, alpha=0.7, label="Full"
        )
        _ax.scatter(
            _years_asc,
            _mdet_fit,
            s=12,
            color=_c_fit,
            alpha=0.7,
            marker="x",
            label="1998+",
        )
        _ax.axhline(_mdet_all.mean(), color=_c_all, lw=1.2, ls="--")
        _ax.axhline(_mdet_fit.mean(), color=_c_fit, lw=1.2, ls="--")
        if _i == 0:
            _ax.legend(fontsize=7)

        # Col 2: |residual| trend with p-values (both)
        # Full-record: center using all-years mean (matches how variance was fit)
        _abs_r_all = np.abs(_mdet_all - _vp_all["resid_mean"])
        _abs_r_fit = np.abs(_mdet_fit - _mdet_fit.mean())
        _spread_all = np.clip(
            _vp_all["intercept_v"] + _vp_all["slope_v"] * _xnorm_asc,
            1e-4,
            None,
        )
        _spread_fit = np.clip(
            _vp_fit["intercept_v"] + _vp_fit["slope_v"] * _xnorm_asc,
            1e-4,
            None,
        )
        _ax = _axes[_i, 2]
        _ax.scatter(_years_asc, _abs_r_all, s=14, color=_c_all, alpha=0.7)
        _ax.scatter(
            _years_asc, _abs_r_fit, s=12, color=_c_fit, alpha=0.7, marker="x"
        )
        _ax.plot(
            _years_asc,
            _spread_all,
            color=_c_all,
            lw=2,
            label=f"Full  p={_vp_all['pvalue_v']:.3f}",
        )
        _ax.plot(
            _years_asc,
            _spread_fit,
            color=_c_fit,
            lw=2,
            ls="--",
            label=f"1998+ p={_vp_fit['pvalue_v']:.3f}",
        )
        _ax.legend(fontsize=7, loc="upper right")

        # Col 3: fully detrended (both)
        _ax = _axes[_i, 3]
        _ax.scatter(
            _years_asc, _fdet_all, s=14, color=_c_all, alpha=0.7, label="Full"
        )
        _ax.scatter(
            _years_asc,
            _fdet_fit,
            s=12,
            color=_c_fit,
            alpha=0.7,
            marker="x",
            label="1998+",
        )
        _ax.axhline(_fdet_all.mean(), color=_c_all, lw=1.2, ls="--")
        _ax.axhline(_fdet_fit.mean(), color=_c_fit, lw=1.2, ls="--")
        if _i == 0:
            _ax.legend(fontsize=7)

    for _j in range(4):
        _axes[-1, _j].set_xlabel("Year")

    plt.suptitle(
        "Detrending steps — blue = full record, red = 1998+",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()
    _fig
    return


@app.cell
def model_selector(mo):
    model_dropdown = mo.ui.dropdown(
        options=["Full record", "1998+"],
        value="Full record",
        label="Detrend model to use for trigger analysis",
    )
    model_dropdown
    return (model_dropdown,)


@app.cell
def select_model(
    beta_results_all,
    beta_results_fit,
    df_detrended_final_all,
    df_detrended_final_fit,
    model_dropdown,
    var_params_all,
    var_params_fit,
):
    if model_dropdown.value == "Full record":
        beta_results = beta_results_all
        var_params = var_params_all
        df_detrended_final = df_detrended_final_all
    else:
        beta_results = beta_results_fit
        var_params = var_params_fit
        df_detrended_final = df_detrended_final_fit
    return beta_results, df_detrended_final, var_params


@app.cell
def merge_aug(df_detrended_final, df_stats_iri):
    df_stats = df_detrended_final.merge(
        df_stats_iri[["year", "Aug", "JAS_SPI"]]
    )
    return (df_stats,)


@app.cell
def _corr_header(mo):
    mo.md(
        """
    ## Correlation with August observation

        Negative correlation between Jan–Jun forecast and Aug observation is what
        drives the forecast arm of the trigger. Detrending should improve this
        by removing the shared time trend.
    """
    )
    return


@app.cell
def jas_spi_plot(df_stats_iri, linregress, plt, start_year):
    _df = (
        df_stats_iri[df_stats_iri["year"] >= start_year][["year", "JAS_SPI"]]
        .dropna(subset=["JAS_SPI"])
        .sort_values("year")
    )
    _years = _df["year"].values.astype(float)
    _spi = _df["JAS_SPI"].values

    _slope, _intercept, _r, _p, _ = linregress(_years, _spi)
    _fit = _intercept + _slope * _years

    _fig, _ax = plt.subplots(figsize=(10, 4))
    _colors = ["crimson" if s < 0 else "#4477AA" for s in _spi]
    _ax.bar(_years, _spi, color=_colors, alpha=0.75, width=0.7)
    _ax.plot(
        _years,
        _fit,
        color="#CCBB44",
        lw=2,
        label=f"Linear trend: {_slope:.3f}/yr, r={_r:.2f}, p={_p:.3f}",
    )
    _ax.axhline(0, color="black", lw=0.8)
    _ax.set_xlabel("Year")
    _ax.set_ylabel("JAS SPI")
    _ax.legend()
    plt.tight_layout()
    _fig
    return


@app.cell
def corr_comparison_plot(COLS, df_stats, df_stats_iri, np, plt, start_year):
    _fig, _ax = plt.subplots(figsize=(8, 5))
    _df_iri_fit = df_stats_iri[df_stats_iri["year"] >= start_year]

    _corr1 = -df_stats[COLS + ["JAS_SPI"]].corr()["JAS_SPI"][COLS]
    _corr2 = -_df_iri_fit[COLS + ["JAS_SPI"]].corr()["JAS_SPI"][COLS]

    _x = np.arange(len(COLS))
    _w = 0.4

    _ax.bar(_x - _w / 2, _corr2.values, width=_w, label="Original")
    _ax.bar(
        _x + _w / 2,
        _corr1.values,
        width=_w,
        label="Detrended",
        color="darkorange",
    )

    _ax.set_xticks(_x)
    _ax.set_xticklabels(COLS)
    _ax.set_title(
        "Negative correlation with JAS SPI (higher = better forecast signal)"
    )
    _ax.axhline(0, color="black", lw=0.8)
    _ax.legend()
    plt.tight_layout()
    _fig
    return


@app.cell
def corr_scatter_plot(
    COLS,
    df_stats,
    df_stats_iri,
    linregress,
    np,
    plt,
    start_year,
):
    _fig, _axes = plt.subplots(2, len(COLS), figsize=(16, 7))
    _df_iri_fit = df_stats_iri[df_stats_iri["year"] >= start_year]

    _row_data = [
        ("Raw", _df_iri_fit),
        ("Detrended", df_stats),
    ]

    for _row, (_label, _df) in enumerate(_row_data):
        _sub = _df[COLS + ["JAS_SPI"]].dropna(subset=["JAS_SPI"])
        _spi = _sub["JAS_SPI"].values

        for _j, _col in enumerate(COLS):
            _ax = _axes[_row, _j]
            _fcast = _sub[_col].values

            # forecast on x, JAS SPI on y
            _ax.scatter(_fcast, _spi, s=18, color="#4477AA", alpha=0.7)

            _slope, _intercept, _r, _p, _ = linregress(_fcast, _spi)
            _x_fit = np.linspace(_fcast.min(), _fcast.max(), 100)
            _ax.plot(
                _x_fit, _intercept + _slope * _x_fit, color="#EE6677", lw=1.5
            )

            _ax.annotate(
                f"r={_r:.2f}\np={_p:.3f}",
                xy=(0.05, 0.82),
                xycoords="axes fraction",
                fontsize=8,
            )

            if _row == 0:
                _ax.set_title(_col, fontsize=10)
            if _j == 0:
                _ax.set_ylabel(f"JAS SPI\n({_label})", fontsize=9)
            _ax.set_xlabel("forecast", fontsize=8)

    plt.suptitle("Forecast vs JAS SPI", fontsize=12, fontweight="bold")
    plt.tight_layout()
    _fig
    return


@app.cell
def roc_auc_plot(
    COLS,
    df_stats,
    df_stats_iri,
    mannwhitneyu,
    mo,
    np,
    plt,
    start_year,
):
    def _auc(y_true, y_score):
        """AUC via Mann-Whitney U (equivalent to trapezoidal ROC AUC)."""
        _pos = y_score[y_true == 1]
        _neg = y_score[y_true == 0]
        if len(_pos) == 0 or len(_neg) == 0:
            return 0.5
        _u, _ = mannwhitneyu(_pos, _neg, alternative="greater")
        return _u / (len(_pos) * len(_neg))

    def _roc_curve(y_true, y_score):
        """Manual ROC curve (FPR, TPR arrays)."""
        _idx = np.argsort(y_score)[::-1]
        _yt = y_true[_idx]
        _n_pos = int(_yt.sum())
        _n_neg = len(_yt) - _n_pos
        _tpr = np.concatenate([[0.0], np.cumsum(_yt) / _n_pos])
        _fpr = np.concatenate([[0.0], np.cumsum(1 - _yt) / _n_neg])
        return _fpr, _tpr

    _df_iri_fit = df_stats_iri[df_stats_iri["year"] >= start_year]
    _row_data = [("Raw", _df_iri_fit), ("Detrended", df_stats)]
    _colors = {"Raw": "#4477AA", "Detrended": "darkorange"}

    # Lower-tercile threshold computed from 1998+ JAS_SPI values
    _spi_all = _df_iri_fit["JAS_SPI"].dropna().values
    _tercile = float(np.percentile(_spi_all, 100 / 3))

    # Compute AUC for all months × raw/detrended
    _aucs = {}
    for _label, _df in _row_data:
        _sub = _df[COLS + ["JAS_SPI"]].dropna(subset=["JAS_SPI"])
        _y_true = (_sub["JAS_SPI"].values < _tercile).astype(float)
        _aucs[_label] = [_auc(_y_true, _sub[_col].values) for _col in COLS]

    # ── bar chart ──────────────────────────────────────────────────────────────
    _fig1, _ax1 = plt.subplots(figsize=(8, 4))
    _x = np.arange(len(COLS))
    _w = 0.4
    _ax1.bar(_x - _w / 2, _aucs["Raw"], width=_w, label="Raw", color="#4477AA")
    _ax1.bar(
        _x + _w / 2,
        _aucs["Detrended"],
        width=_w,
        label="Detrended",
        color="darkorange",
    )
    _ax1.axhline(0.5, color="gray", lw=1, ls="--", label="random")
    _ax1.set_xticks(_x)
    _ax1.set_xticklabels(COLS)
    _ax1.set_ylim(0, 1)
    _ax1.set_ylabel("AUC")
    _ax1.set_title(
        f"ROC AUC — forecast vs JAS SPI < {_tercile:.2f} (lower tercile)"
    )
    _ax1.legend()
    plt.tight_layout()

    # ── ROC curves ─────────────────────────────────────────────────────────────
    _fig2, _axes2 = plt.subplots(2, 3, figsize=(12, 7))
    for _i, _col in enumerate(COLS):
        _ax = _axes2[_i // 3, _i % 3]
        for _label, _df in _row_data:
            _sub = _df[[_col, "JAS_SPI"]].dropna(subset=["JAS_SPI"])
            _yt = (_sub["JAS_SPI"].values < _tercile).astype(float)
            _fpr, _tpr = _roc_curve(_yt, _sub[_col].values)
            _a = _auc(_yt, _sub[_col].values)
            _ax.plot(
                _fpr,
                _tpr,
                color=_colors[_label],
                lw=1.5,
                label=f"{_label} (AUC={_a:.2f})",
            )
        _ax.plot([0, 1], [0, 1], color="gray", lw=0.8, ls="--")
        _ax.set_title(_col)
        _ax.set_xlim(0, 1)
        _ax.set_ylim(0, 1)
        if _i % 3 == 0:
            _ax.set_ylabel("TPR")
        if _i // 3 == 1:
            _ax.set_xlabel("FPR")
        _ax.legend(fontsize=8)
    plt.suptitle(
        f"ROC curves — forecast vs JAS SPI < {_tercile:.2f} (lower tercile)",
        fontsize=12,
        fontweight="bold",
    )
    plt.tight_layout()

    mo.vstack([_fig1, _fig2])
    return


@app.cell
def _trigger_header(mo):
    mo.md(
        """
    ## Trigger design

        Grid search over all combinations of forecast-arm threshold (top N years
        above) and observation-arm threshold (bottom N years below). The plot shows
        which combinations achieve an overall return period between 3 and 5 years.
    """
    )
    return


@app.cell
def params(mo):
    mos = [1, 2, 3, 4, 5, 6]
    start_year = 1998
    end_year = 2025
    total_years = end_year - start_year + 1
    rp_target = 3.5
    n_years_overall_target = int((total_years + 1) / rp_target)
    _actual_rp = (total_years + 1) / n_years_overall_target
    mo.md(
        f"Target RP: **{rp_target}**, "
        f"n trigger years: **{n_years_overall_target}**, "
        f"actual RP: **{_actual_rp:.2f}** "
        f"({start_year}–{end_year}, N={total_years})"
    )
    return mos, start_year


@app.cell
def grid_search(calendar, df_stats, mos, np, pd, start_year):
    _dicts = []
    df_model = df_stats[df_stats["year"] >= start_year].copy()
    _n = len(df_model)

    for _n_above in range(0, _n + 1):
        for _mo in mos:
            _col = calendar.month_abbr[_mo]
            _thresh = (
                df_model[_col].nlargest(_n_above).min()
                if _n_above > 0
                else np.inf
            )
            df_model[f"trig_{_mo}"] = df_model[_col] >= _thresh

        _consec_cols = []
        for _second_mo in mos[1:]:
            _first_mo = _second_mo - 1
            _consec_col = f"trig_{_first_mo}_{_second_mo}"
            df_model[_consec_col] = (
                df_model[f"trig_{_first_mo}"] & df_model[f"trig_{_second_mo}"]
            )
            _consec_cols.append(_consec_col)
        df_model["trig_fcast"] = df_model[_consec_cols].any(axis=1)
        _n_fcast = int(df_model["trig_fcast"].sum())

        for _n_below in range(0, _n + 1):
            _thresh_o = (
                df_model["Aug"].nsmallest(_n_below).max()
                if _n_below > 0
                else -np.inf
            )
            df_model["trig_obsv"] = df_model["Aug"] <= _thresh_o
            _n_obsv = int(df_model["trig_obsv"].sum())
            df_model["trig_either"] = (
                df_model["trig_fcast"] | df_model["trig_obsv"]
            )
            _n_trig = int(df_model["trig_either"].sum())
            _dicts.append(
                {
                    "n_above": _n_above,
                    "n_below": _n_below,
                    "n_fcast": _n_fcast,
                    "n_obsv": _n_obsv,
                    "n_trig": _n_trig,
                }
            )

    df_qs = pd.DataFrame(_dicts).drop_duplicates(subset=["n_fcast", "n_obsv"])
    return df_model, df_qs


@app.cell
def rp_trade_off_plot(df_model, df_qs, plt):
    _df_qs_plot = df_qs.copy()
    _df_qs_plot["rp"] = (len(df_model) + 1) / _df_qs_plot["n_trig"]
    _df_qs_filt = _df_qs_plot[_df_qs_plot["rp"].between(3, 5)].drop_duplicates(
        subset=["n_fcast", "n_obsv"]
    )

    _rp_vals = sorted(_df_qs_filt["rp"].round(1).unique())
    _cmap = plt.colormaps.get_cmap("tab10")
    _color_map = {v: _cmap(i) for i, v in enumerate(_rp_vals)}

    _fig, _ax = plt.subplots(figsize=(7, 6))
    for _rp_val, _group in _df_qs_filt.groupby(_df_qs_filt["rp"].round(1)):
        _ax.scatter(
            _group["n_fcast"],
            _group["n_obsv"],
            color=_color_map[_rp_val],
            s=120,
            edgecolors="gray",
            linewidths=0.4,
            label=f"RP {_rp_val:.1f}",
        )

    _ax.axhline(0, color="black", lw=0.8)
    _ax.axvline(0, color="black", lw=0.8)
    _ax.axline((0, 0), slope=1, color="gray", lw=1, ls="--", label="45°")
    _ax.legend(title="Overall RP", bbox_to_anchor=(1.05, 1), loc="upper left")
    _ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    _ax.set_xlabel("N years triggered by forecast arm")
    _ax.set_ylabel("N years triggered by observation arm")
    _ax.set_xlim(-0.5, 10.5)
    _ax.set_ylim(-0.5, 10.5)
    _ax.xaxis.set_major_locator(plt.MultipleLocator(1))
    _ax.yaxis.set_major_locator(plt.MultipleLocator(1))
    plt.tight_layout()
    _fig
    return


@app.cell
def selector_ui(df_qs, mo):
    _n_fcast_opts = sorted(df_qs["n_fcast"].unique().tolist())
    _n_obsv_opts = sorted(df_qs["n_obsv"].unique().tolist())
    n_fcast_dropdown = mo.ui.dropdown(
        options=_n_fcast_opts,
        value=5,
        label="Forecast arm trigger years",
    )
    n_obsv_dropdown = mo.ui.dropdown(
        options=_n_obsv_opts,
        value=5,
        label="Observation arm trigger years",
    )
    mo.hstack([n_fcast_dropdown, n_obsv_dropdown])
    return n_fcast_dropdown, n_obsv_dropdown


@app.cell
def select_thresholds(df_qs, n_fcast_dropdown, n_obsv_dropdown):
    n_fcast_sel = n_fcast_dropdown.value
    n_obsv_sel = n_obsv_dropdown.value

    _row = df_qs[
        (df_qs["n_fcast"] == n_fcast_sel) & (df_qs["n_obsv"] == n_obsv_sel)
    ].iloc[0]

    n_above = int(_row["n_above"])
    n_below = int(_row["n_below"])
    return n_above, n_below


@app.cell
def compute_trigger_df(calendar, df_stats, mos, n_above, n_below, np):
    df_disp = df_stats.copy()

    for _mo in mos:
        _col = calendar.month_abbr[_mo]
        _thresh = (
            df_disp[_col].nlargest(n_above).min() if n_above > 0 else np.inf
        )
        df_disp[f"trig_{_col}"] = df_disp[_col] >= _thresh

    for _second_mo in mos[1:]:
        _first_mo = _second_mo - 1
        _fc = calendar.month_abbr[_first_mo]
        _sc = calendar.month_abbr[_second_mo]
        df_disp[f"trig_{_fc}_{_sc}"] = (
            df_disp[f"trig_{_fc}"] & df_disp[f"trig_{_sc}"]
        )

    _thresh_o = (
        df_disp["Aug"].nsmallest(n_below).max() if n_below > 0 else -np.inf
    )
    df_disp["trig_fcast"] = df_disp[
        [
            f"trig_{calendar.month_abbr[mos[0]]}_{calendar.month_abbr[mos[1]]}",
            *[
                f"trig_{calendar.month_abbr[m-1]}_{calendar.month_abbr[m]}"
                for m in mos[2:]
            ],
        ]
    ].any(axis=1)
    df_disp["trig_obsv"] = df_disp["Aug"] <= _thresh_o
    df_disp["trig_either"] = df_disp["trig_fcast"] | df_disp["trig_obsv"]
    return (df_disp,)


@app.cell
def show_trigger_detail(calendar, df_disp, mos):
    def _style_bool(val):
        if val is True:
            return "background-color: crimson; color: white; font-weight: 500"
        return ""

    _month_cols = [f"trig_{calendar.month_abbr[mo]}" for mo in mos]
    _consec_cols = [
        f"trig_{calendar.month_abbr[m-1]}_{calendar.month_abbr[m]}"
        for m in mos[1:]
    ]

    _df_detail = df_disp[["year"] + _month_cols + _consec_cols].copy()
    _df_detail.columns = (
        ["year"]
        + [calendar.month_abbr[mo] for mo in mos]
        + [
            f"{calendar.month_abbr[m-1]}+{calendar.month_abbr[m]}"
            for m in mos[1:]
        ]
    )

    detail_styled = (
        _df_detail.set_index("year")
        .style.map(_style_bool)
        .set_caption("Per-month and consecutive triggers")
    )
    detail_styled
    return


@app.cell
def show_trigger_summary(df_disp):
    def _style_bool(val):
        if val is True:
            return "background-color: crimson; color: white; font-weight: 500"
        return ""

    _df_summary = df_disp[
        ["year", "trig_fcast", "trig_obsv", "trig_either"]
    ].copy()
    _df_summary.columns = ["year", "forecast", "observation", "either"]

    summary_styled = (
        _df_summary.set_index("year")
        .style.map(_style_bool)
        .set_caption("Overall forecast / observation triggers")
    )
    summary_styled
    return


@app.cell
def show_threshold_table(calendar, df_model, mo, mos, n_above, n_below, np):
    _n = len(df_model)
    _pct_fcast = n_above / _n * 100
    _pct_obsv = n_below / _n * 100

    _rows = []
    for _mo in mos:
        _col = calendar.month_abbr[_mo]
        _thresh = (
            df_model[_col].nlargest(n_above).min() if n_above > 0 else np.inf
        )
        _rows.append(f"| {_col} | ≥ | {_thresh:.3f} | top {_pct_fcast:.1f}% |")
    _thresh_o = (
        df_model["Aug"].nsmallest(n_below).max() if n_below > 0 else -np.inf
    )
    _rows.append(
        f"| Aug (obs) | ≤ | {_thresh_o:.3f} | bottom {_pct_obsv:.1f}% |"
    )
    _table = (
        "| Month | dir | threshold (detrended) | percentile |\n|---|---|---|---|\n"
        + "\n".join(_rows)
    )
    mo.md(
        f"### Thresholds\n\n"
        f"Forecast arm: top **{n_above}** / **{_n}** yrs per month = **{_pct_fcast:.1f}%** each.  \n"
        f"Observation arm: bottom **{n_below}** / **{_n}** yrs = **{_pct_obsv:.1f}%**.\n\n"
        f"{_table}"
    )
    return


@app.cell
def _backtransform_header(mo):
    mo.md(
        """
    ## Back-transformed thresholds

        The trigger thresholds above are in detrended space. To use them in
        practice we need to back-transform to raw values for each future year,
        accounting for the ongoing trend.
    """
    )
    return


@app.cell
def back_transform(
    beta_results,
    calendar,
    df_model,
    df_stats_iri,
    mos,
    n_above,
    np,
    pd,
    plt,
    var_params,
    x_norm_fit,
    years_fit,
):
    _future_years = [2026, 2027]
    _year_start = df_stats_iri["year"].values[
        0
    ]  # most recent year in full dataset

    _thresh_rows = []
    _thresh_per_year_all = {}
    _trend_all = {}

    for _mo in mos:
        _col = calendar.month_abbr[_mo]
        _res = beta_results[_col]
        _vp = var_params[_col]

        # Threshold is in fully-detrended space (after mean + variance detrend)
        _thresh_final = (
            df_model[_col].nlargest(n_above).min() if n_above > 0 else np.inf
        )

        # --- invert step 1: mean (beta) detrend ---
        # mean_trend must match what was used in the forward transform
        # (fittedvalues.mean() = mean over training data, correct for both models)
        _X_hist = np.column_stack([np.ones(len(years_fit)), x_norm_fit])
        _trend = _res.predict(_X_hist)
        _mean_trend = _res.fittedvalues.mean()

        # --- invert step 2: variance detrend ---
        # detrended = (beta_det - resid_mean) / fitted_spread * abs_resid_mean + resid_mean
        # => beta_det = (detrended - resid_mean) * fitted_spread / abs_resid_mean + resid_mean
        _fitted_spread = np.clip(
            _vp["intercept_v"] + _vp["slope_v"] * x_norm_fit, 1e-3, None
        )
        _thresh_beta = (
            _thresh_final - _vp["resid_mean"]
        ) * _fitted_spread / _vp["abs_resid_mean"] + _vp["resid_mean"]

        # --- invert step 1 ---
        # beta_det = y / trend * mean_trend  =>  y = beta_det * trend / mean_trend
        _thresh_per_year_all[_col] = _thresh_beta * _trend / _mean_trend
        _trend_all[_col] = _trend

        # Future years
        _future_thresholds = {}
        for _yr in _future_years:
            _x_f = _yr - _year_start
            _trend_f = _res.predict(np.array([[1, _x_f]]))[0]
            _spread_f = max(_vp["intercept_v"] + _vp["slope_v"] * _x_f, 1e-3)
            _beta_thresh_f = (
                _thresh_final - _vp["resid_mean"]
            ) * _spread_f / _vp["abs_resid_mean"] + _vp["resid_mean"]
            _future_thresholds[_yr] = round(
                _beta_thresh_f * _trend_f / _mean_trend, 4
            )

        _thresh_rows.append(
            {
                "month": _col,
                "detrended_thresh": round(_thresh_final, 4),
                "mean_trend": round(_mean_trend, 4),
                **{
                    f"thresh_{yr}": _future_thresholds[yr]
                    for yr in _future_years
                },
            }
        )

    df_thresh_summary = pd.DataFrame(_thresh_rows).set_index("month")

    # Plot: 2×3 grid, one subplot per month — raw data + trend + threshold
    _idx = np.argsort(years_fit)
    _years_asc = years_fit[_idx]
    _df_raw = df_stats_iri[df_stats_iri["year"] >= years_fit.min()]

    _fig, _axes = plt.subplots(2, 3, figsize=(15, 8))
    for _i, _mo in enumerate(mos):
        _col = calendar.month_abbr[_mo]
        _ax = _axes[_i // 3, _i % 3]

        # Years that triggered in detrended space (ground truth)
        _thresh_final = (
            df_model[_col].nlargest(n_above).min() if n_above > 0 else np.inf
        )
        _trig_yrs = set(
            df_model.loc[df_model[_col] >= _thresh_final, "year"].values
        )
        _raw_vals = _df_raw[_col].values[_idx]
        _trig_mask = np.array([y in _trig_yrs for y in _years_asc])

        # Non-triggered background scatter
        _ax.scatter(
            _years_asc[~_trig_mask],
            _raw_vals[~_trig_mask],
            s=15,
            color="#4477AA",
            alpha=0.7,
            label="raw data",
        )
        # Triggered years (detrended ground truth) in crimson
        _ax.scatter(
            _years_asc[_trig_mask],
            _raw_vals[_trig_mask],
            s=50,
            color="crimson",
            zorder=5,
            alpha=0.9,
            label=f"triggered ({n_above})",
        )
        _ax.plot(
            _years_asc,
            _trend_all[_col][_idx],
            color="#EE6677",
            lw=2,
            label="beta trend",
        )
        _ax.plot(
            _years_asc,
            _thresh_per_year_all[_col][_idx],
            color="#CCBB44",
            lw=1.5,
            ls="--",
            label="threshold",
        )

        for _yr in _future_years:
            _t_raw = df_thresh_summary.loc[
                calendar.month_abbr[_mo], f"thresh_{_yr}"
            ]
            _ax.scatter(_yr, _t_raw, s=60, color="#CCBB44", zorder=5)
            _ax.annotate(
                f"{_yr}: {_t_raw:.3f}",
                (_yr, _t_raw),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )

        _ax.set_title(calendar.month_abbr[_mo])
        _ax.set_ylim(bottom=0)
        if _i == 0:
            _ax.legend(fontsize=8)

    for _j in range(3):
        _axes[1, _j].set_xlabel("Year")

    plt.suptitle(
        "Raw data + beta trend + trigger threshold (back-transformed)",
        fontsize=12,
    )
    plt.tight_layout()
    _fig
    return (df_thresh_summary,)


@app.cell
def show_thresh_summary(df_thresh_summary, n_above):
    thresh_summary_styled = df_thresh_summary.style.format(
        "{:.4f}"
    ).set_caption(
        f"Back-transformed thresholds (forecast arm, top {n_above} years)"
    )
    thresh_summary_styled
    return


if __name__ == "__main__":
    app.run()
