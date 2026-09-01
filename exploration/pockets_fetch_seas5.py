"""Recompute current SEAS5 skill/forecast stats for Niger admin units.

Reuses the team's ds-seas5-skill methodology directly (its ``src.skill``
module, imported from the sibling clone): SEAS5 and ERA5 monthly means per
pcode from the prod DB, trimester aggregation (including the in-season
"mixed" trimesters that blend already-observed ERA5 months with the current
issuance), log-space normalization, Pearson-r skill, and empirical
(Weibull) return periods of the current forecast.

Why not read the app's published parquets? Their issued-August in-season
rows (JJA/JAS) were computed before ERA5 July 2026 landed and silently fell
back to the 2025 issuance (the documented vintage race), so the 2026
in-season composites must be recomputed here. ERA5 valid through 2026-07
and SEAS5 issued 2026-08 were verified in the DB before running.

Output: ``exploration/public/pockets/seas5_skill_ner.csv`` — one row per
pcode x trimester (JJA/JAS/ASO/SON, issued August), with pearson_r,
forecast percentile / RP for season-year 2026, and the paired-years count.

Usage: ``uv run python exploration/pockets_fetch_seas5.py``
"""

import sys
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd

SEAS5_SKILL_REPO = Path(__file__).resolve().parents[2] / "ds-seas5-skill"
sys.path.insert(0, str(SEAS5_SKILL_REPO))

from src.datasources.era5 import load_era5  # noqa: E402
from src.datasources.seas5 import load_seas5  # noqa: E402
from src.skill import (  # noqa: E402
    TRIMESTERS,
    aggregate_era5_trimester,
    aggregate_mixed_trimester,
    aggregate_seas5_trimester,
    compute_skill_metrics,
    empirical_rp,
    normalize_seas5,
    trimester_lead,
)

ISSUED_MONTH = 8
TRIMS = ["JJA", "JAS", "ASO", "SON"]
SEASON_YEAR = 2026
OUT = Path(__file__).parent / "public" / "pockets" / "seas5_skill_ner.csv"


def combo_stats(df_s_all, df_e_all, trimester):
    valid_months = TRIMESTERS[trimester]
    if trimester_lead(ISSUED_MONTH, valid_months) in (-1, -2):
        df_s_raw = aggregate_mixed_trimester(
            df_s_all, df_e_all, ISSUED_MONTH, valid_months
        )
    else:
        df_s_raw = aggregate_seas5_trimester(
            df_s_all[df_s_all["issued_date"].dt.month == ISSUED_MONTH],
            ISSUED_MONTH,
            valid_months,
        )
    df_e_raw = aggregate_era5_trimester(df_e_all, valid_months)
    if df_s_raw.empty or df_e_raw.empty:
        return None

    df_s_log = df_s_raw.assign(
        forecast_mean=np.log1p(df_s_raw["forecast_mean"].clip(lower=0))
    )
    df_e_log = df_e_raw.assign(
        obs_mean=np.log1p(df_e_raw["obs_mean"].clip(lower=0))
    )
    df_s_norm = normalize_seas5(df_s_log, df_e_log)

    raw = _forecast_position(df_s_norm, df_e_log)
    if raw is None:
        return None
    dt = _forecast_position(*_detrend(df_s_norm, df_e_log))
    row = {"trimester": trimester, **raw}
    if dt is not None:
        row.update({f"{k}_dt": v for k, v in dt.items()})
    return row


def _forecast_position(df_s, df_e):
    """Skill + the 2026 forecast's position in the historical distribution."""
    skill = compute_skill_metrics(df_s, df_e)
    if skill is None:
        return None
    cur = df_s[df_s["season_year"] == SEASON_YEAR]
    if cur.empty:
        return None
    fc = float(cur["forecast_mean"].iloc[0])
    hist = df_s.merge(df_e, on="season_year")
    hist_f = hist.loc[
        hist["season_year"] < SEASON_YEAR, "forecast_mean"
    ].values
    return {
        "pearson_r": skill["pearson_r"],
        "n_years": skill["n_years"],
        "forecast_mean_log": fc,
        "forecast_percentile": 100.0 * float(np.mean(hist_f <= fc)),
        "forecast_rp": empirical_rp(fc, hist_f, higher_is_more_extreme=False),
        "n_hist": len(hist_f),
    }


def _detrend(df_s_norm, df_e_log):
    """Linear detrend of both sides in log space, as in run_all_combinations.

    Fit over the forecast/obs overlap years, subtract from ALL years
    (including the current forecast), re-add the overlap mean.
    """
    hist_yrs = sorted(
        set(df_e_log["season_year"]) & set(df_s_norm["season_year"])
    )
    if len(hist_yrs) < 2:
        return df_s_norm, df_e_log
    x_hist = np.array(hist_yrs, dtype=float)
    a_mat = np.column_stack([x_hist, np.ones(len(x_hist))])

    fc_hist = (
        df_s_norm[df_s_norm["season_year"].isin(hist_yrs)]
        .sort_values("season_year")["forecast_mean"]
        .values
    )
    a, b = np.linalg.lstsq(a_mat, fc_hist, rcond=None)[0]
    x_s = df_s_norm["season_year"].values.astype(float)
    df_s_dt = df_s_norm.assign(
        forecast_mean=df_s_norm["forecast_mean"].values
        - (a * x_s + b)
        + fc_hist.mean()
    )

    obs_hist = (
        df_e_log[df_e_log["season_year"].isin(hist_yrs)]
        .sort_values("season_year")["obs_mean"]
        .values
    )
    a, b = np.linalg.lstsq(a_mat, obs_hist, rcond=None)[0]
    x_e = df_e_log["season_year"].values.astype(float)
    df_e_dt = df_e_log.assign(
        obs_mean=df_e_log["obs_mean"].values - (a * x_e + b) + obs_hist.mean()
    )
    return df_s_dt, df_e_dt


def main():
    adm1 = stratus.codab.load_codab_from_blob("ner", admin_level=1)
    adm2 = stratus.codab.load_codab_from_blob("ner", admin_level=2)
    units = [
        (p, 1, n) for p, n in zip(adm1["ADM1_PCODE"], adm1["ADM1_FR"])
    ] + [(p, 2, n) for p, n in zip(adm2["ADM2_PCODE"], adm2["ADM2_FR"])]

    rows = []
    for pcode, level, name in units:
        try:
            df_s = load_seas5(pcode)
            df_e = load_era5(pcode)
        except Exception as e:
            print(f"{pcode} load failed: {e}", flush=True)
            continue
        for trim in TRIMS:
            st = combo_stats(df_s, df_e, trim)
            if st is None:
                print(f"{pcode} {trim}: no stats", flush=True)
                continue
            rows.append(
                {"pcode": pcode, "adm_level": level, "name": name, **st}
            )
        print(f"{pcode} ({name}) done", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()
