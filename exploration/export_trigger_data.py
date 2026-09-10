"""Export raw historical trigger data for the Niger drought IRI-based trigger.

Replicates the DEFAULT design of the deployed marimo explorer
(``exploration/rolling_threshold_marimo.py`` -> GitHub Pages) and writes
self-contained CSVs to ``exports/`` (see ``exports/README.md``):

  iri_maproom_raw.csv          raw IRI Maproom export (the authoritative input)
  forecast_month_thresholds.csv per year x month: rolling threshold, actual, trigger
  trigger_history.csv          annual per-pair + arm + window trigger record

Authoritative deployment (defaults): https://ocha-dap.github.io/ds-aa-ner-drought/

Trigger design (two independent arms, OR):
  Forecast arm  -- IRI below-normal probability (OCHA Certification model, 35%
                   frequency). For each of Jan..Jun, the month "fires" if its value
                   is in the top FORECAST_PCT% of its rolling REF_WINDOW-year window
                   (threshold locked to the k-th highest actual value, k=ceil(p*n)).
                   The arm fires if any two CONSECUTIVE months both fire.
  Observation arm -- ENACTS Jun-Jul SPI (column ``Aug``). Fires if the value is in the
                   bottom OBS_PCT% of the FULL historical record (single fixed threshold).

Windows (per the authoritative deployment). Each consecutive pair is assigned to a
window by its DECISION month = the later month of the pair:
  wt1 = Window 1 (decisions Feb-Mar): pairs Jan+Feb, Feb+Mar
  wt2 = Window 2 (decisions Apr-Jun, or Aug obs): pairs Mar+Apr, Apr+May, May+Jun, or obs
The Mar+Apr pair (decided in April) belongs to Window 2. It fires in 2001, so 2001
triggers BOTH windows -- matching the authoritative per-window stats (F1: 3 years,
RP 8.7; F2: 6 years, RP 4.3; global: 8 years, RP 3.3).
"""

import calendar
from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "exports"

BLOB = "ds-aa-ner-drought/raw/iri/ner_maproom_export_2026-04-25_thresh35 - Sheet1.csv"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
REF_WINDOW = 10
START_EVAL = 2001  # first year with a full 10-yr reference window (data starts 1991)
END_EVAL = 2025
FORECAST_PCT = 35  # marimo slider default
OBS_PCT = 15  # marimo slider default
RP_TARGET = 3.5

PAIRS = [(MONTHS[i], MONTHS[i + 1]) for i in range(len(MONTHS) - 1)]
# Each pair assigned by its decision (later) month: Mar+Apr -> Window 2.
W1_PAIRS = ["Jan+Feb", "Feb+Mar"]
W2_PAIRS = ["Mar+Apr", "Apr+May", "May+Jun"]


def load_raw():
    df = stratus.load_csv_from_blob(BLOB)
    df.columns = ["year", *MONTHS, "Aug", "JAS_SPI"]
    df["year"] = df["year"].astype(int)
    df[MONTHS] = df[MONTHS] / 100.0  # % -> fraction
    return df.sort_values("year").reset_index(drop=True)


def main():
    EXPORT_DIR.mkdir(exist_ok=True)
    df = load_raw()

    # raw export (percentages as originally supplied, plus obs cols)
    raw_out = df.copy()
    raw_out[MONTHS] = (raw_out[MONTHS] * 100).round(1)
    raw_out = raw_out.sort_values("year", ascending=False)
    raw_out.to_csv(EXPORT_DIR / "iri_maproom_raw.csv", index=False)

    # observational arm: bottom OBS_PCT% of full record (fixed threshold)
    all_aug = sorted(df["Aug"].values)
    k_obs = int(np.ceil(OBS_PCT / 100 * len(all_aug)))
    obs_thresh = float(all_aug[k_obs - 1])

    eval_years = list(range(START_EVAL, END_EVAL + 1))
    thresh_rows, hist_rows = [], []

    for year in eval_years:
        ref = df[df["year"].between(year - REF_WINDOW, year - 1)]
        act = df[df["year"] == year].iloc[0]
        k = int(np.ceil(FORECAST_PCT / 100 * len(ref)))

        month_trig = {}
        for m in MONTHS:
            thr = float(sorted(ref[m].values, reverse=True)[k - 1])
            trig = float(act[m]) >= thr
            month_trig[m] = trig
            thresh_rows.append(
                {
                    "year": year,
                    "month": m,
                    "rolling_threshold": round(thr * 100, 1),
                    "actual_prob": round(float(act[m]) * 100, 1),
                    "triggered": trig,
                }
            )

        pair_trig = {
            f"{a}+{b}": bool(month_trig[a] and month_trig[b]) for a, b in PAIRS
        }
        forecast_arm = any(pair_trig.values())
        obs_arm = float(act["Aug"]) <= obs_thresh
        wt1 = any(pair_trig[p] for p in W1_PAIRS)
        wt2 = any(pair_trig[p] for p in W2_PAIRS) or obs_arm

        hist_rows.append(
            {
                "year": year,
                **{p.lower().replace("+", "_"): int(v) for p, v in pair_trig.items()},
                "forecast_arm": int(forecast_arm),
                "obs_arm": int(obs_arm),
                "aug_spi": float(act["Aug"]),
                "obs_threshold": round(obs_thresh, 3),
                "ner_drought_v1_wt1": bool(wt1),
                "ner_drought_v1_wt2": bool(wt2),
                "either": bool(forecast_arm or obs_arm),
            }
        )

    pd.DataFrame(thresh_rows).to_csv(
        EXPORT_DIR / "forecast_month_thresholds.csv", index=False
    )
    hist = pd.DataFrame(hist_rows)
    hist.to_csv(EXPORT_DIR / "trigger_history.csv", index=False)

    # per-trigger stats (Weibull: RP = (n+1)/k, annual activation prob = k/(n+1))
    n_years = END_EVAL - START_EVAL + 1

    def _round_half_up(x, dp=0):
        f = 10**dp
        return np.floor(x * f + 0.5) / f

    stats_rows = []
    for label, col in [
        ("Window 1", "ner_drought_v1_wt1"),
        ("Window 2", "ner_drought_v1_wt2"),
        ("Global (either)", "either"),
    ]:
        yrs = list(hist.loc[hist[col].astype(bool), "year"])
        k = len(yrs)
        rp = _round_half_up((n_years + 1) / k, 1) if k else float("inf")
        prob = int(_round_half_up(100 * k / (n_years + 1))) if k else 0
        stats_rows.append(
            {
                "trigger": label,
                "return_period_yrs": rp,
                "activation_prob": f"{prob}%",
                "n_activations": k,
                "activated_years": ", ".join(str(y) for y in yrs),
            }
        )
    stats = pd.DataFrame(stats_rows)
    stats.to_csv(EXPORT_DIR / "trigger_stats.csv", index=False)

    print(f"forecast k=ceil({FORECAST_PCT}%*{REF_WINDOW})={k}   "
          f"obs threshold (bottom {OBS_PCT}%) = {obs_thresh:.3f}   n_years={n_years}")
    print(hist.to_string(index=False))
    print()
    print(stats.to_string(index=False))
    print(f"\nwrote 4 files -> {EXPORT_DIR}")
    return hist


if __name__ == "__main__":
    main()
