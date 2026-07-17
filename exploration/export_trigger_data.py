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

Windows (per framework request):
  wt1 = Window 1 (Jan/Feb/Mar forecast): pairs Jan+Feb, Feb+Mar, Mar+Apr
  wt2 = Window 2 (Apr/May/Jun forecast OR Aug obs): pairs Apr+May, May+Jun, or the obs arm
The Mar+Apr pair straddles the two windows; it is assigned to wt1 so that
wt1 OR wt2 exactly reconstructs the authoritative "either-arm" record. (In this
dataset Mar+Apr only fires in 2001, which already triggers wt1 via the other pairs,
so the assignment has no effect on the result.)
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
W1_PAIRS = ["Jan+Feb", "Feb+Mar", "Mar+Apr"]  # Mar+Apr assigned to W1 (see docstring)
W2_PAIRS = ["Apr+May", "May+Jun"]


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

    n = hist["either"].sum()
    print(f"forecast k=ceil({FORECAST_PCT}%*{REF_WINDOW})={k}   "
          f"obs threshold (bottom {OBS_PCT}%) = {obs_thresh:.3f}")
    print(hist.to_string(index=False))
    print(f"\nEITHER (authoritative): "
          f"{list(hist.loc[hist['either'], 'year'])}  "
          f"= {n} yrs, RP={round((END_EVAL - START_EVAL + 2) / n, 2)}")
    print(f"W1: {list(hist.loc[hist['ner_drought_v1_wt1'], 'year'])}")
    print(f"W2: {list(hist.loc[hist['ner_drought_v1_wt2'], 'year'])}")
    print(f"\nwrote 3 files -> {EXPORT_DIR}")
    return hist


if __name__ == "__main__":
    main()
