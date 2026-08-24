---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.19.1
  kernelspec:
    display_name: ds-aa-ner-drought
    language: python
    name: ds-aa-ner-drought
---

# IRI trend
<!-- markdownlint-disable-line MD013 -->
Check trend of overall activation prob.

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import calendar
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch
import ocha_stratus as stratus

from src.constants import *
```

## Load and process data

```python
blob_name = f"{PROJECT_PREFIX}/raw/iri/ner_trigger_comparison_2025_newmodel_adjustment - raw.csv"
```

```python
df_iri_raw = stratus.load_csv_from_blob(blob_name, skiprows=3).dropna()
df_iri_raw.columns = ["year"] + [
    calendar.month_abbr[x] for x in [y for y in range(1, 7)] + [8]
]
df_iri_raw["year"] = df_iri_raw["year"].astype(int)
```

## Calculate activation prob. and plot

See how activation probability changes as we adjust start year of analysis (we have previously used 1998 as a convention, since there were several activations before this).

```python
def calculate_activations(ind_frac: float, print_threshs: bool = False):
    """Calculate activations based on logic in framework"""
    df_iri = df_iri_raw.copy()
    for x in df_iri:
        if "bool" in x or x == "year":
            continue
        if x == "Aug":
            thresh = df_iri[x].quantile(ind_frac)
            thresh = round(thresh, 3)
            df_iri[f"{x}_bool"] = df_iri[x] <= thresh
        else:
            thresh = df_iri[x].quantile(1 - ind_frac)
            thresh = round(thresh, 1)
            df_iri[f"{x}_bool"] = df_iri[x] >= thresh
        if print_threshs:
            print(x, thresh)

    for mo_int in range(1, 6):
        mo1 = calendar.month_abbr[mo_int]
        mo2 = calendar.month_abbr[mo_int + 1]
        df_iri[f"{mo1}{mo2}_consec"] = (
            df_iri[f"{mo1}_bool"] & df_iri[f"{mo2}_bool"]
        )

    cols_w1 = ["JanFeb_consec", "FebMar_consec"]
    df_iri["w1"] = df_iri[cols_w1].any(axis=1)

    cols_w2 = ["MarApr_consec", "AprMay_consec", "MayJun_consec", "Aug_bool"]
    df_iri["w2"] = df_iri[cols_w2].any(axis=1)

    df_iri["any"] = df_iri["w1"] | df_iri["w2"]

    dicts = []
    for year in df_iri["year"].unique():
        dff = df_iri[df_iri["year"] >= year]
        n_years = len(dff)
        n_activations = dff["any"].sum()
        rp = (n_years + 1) / n_activations if n_activations > 0 else np.inf
        prob = 1 / rp
        p = n_activations / n_years
        # Bernoulli standard error
        se = np.sqrt((p * (1 - p) / n_years))
        dicts.append(
            {"min_year": year, "rp": rp, "prob": 1 / rp, "se": se, "p": p}
        )

    df_rp = pd.DataFrame(dicts)
    df_rp["upper_p"] = df_rp["p"] + df_rp["se"]
    df_rp["lower_p"] = df_rp["p"] - df_rp["se"]

    return df_rp, df_iri
```

```python
def plot_rp(df_rp: pd.DataFrame, ind_frac: float):
    max_year = 2020

    fig, ax = plt.subplots(dpi=200)
    df_rp.plot(x="min_year", y="p", ax=ax, color="dodgerblue", legend=False)
    ax.fill_between(
        df_rp["min_year"],
        df_rp["lower_p"],
        df_rp["upper_p"],
        facecolor="dodgerblue",
        alpha=0.3,
    )
    ax.axhline(0.35, color="crimson")
    ax.annotate(
        "0.35 ",
        (df_rp["min_year"].min(), 0.35),
        va="center",
        ha="right",
        color="crimson",
    )

    ax.set_xlim(left=df_rp["min_year"].min(), right=max_year)
    ax.set_ylim(0, 1)

    ax.set_title("Niger drought activation probability estimation")
    ax.text(
        0.5,
        1,
        f"Shaded area ± 1 std. error\nPer-month activation probability {ind_frac:.2f}",
        transform=ax.transAxes,
        ha="center",
        va="top",
    )
    ax.set_ylabel("Overall activation probability")
    ax.set_xlabel("Start year of analysis")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
```

From plot below, activation probability is too high no matter how late we set the start date of analysis.

```python
ind_frac = 0.35
df_rp, df_activations = calculate_activations(ind_frac=ind_frac)
plot_rp(df_rp, ind_frac)
```

```python
df_rp
```

However, if we adjust the per-month percentile threshold to `0.3`, we're ok.

Note that this is set to step of `0.05` since this is how the Maproom is designed.

```python
ind_frac = 0.3
df_rp, df_activations = calculate_activations(ind_frac=ind_frac)
plot_rp(df_rp, ind_frac)
```

## Calculate framework stats

To go in standard reporting table.

```python
ind_frac = 0.3
df_rp, df_activations = calculate_activations(
    ind_frac=ind_frac, print_threshs=True
)
```

```python
df_activations.sort_values("Jan")
```

```python
df_rp
```

```python
WINDOW_1_BUDGET = 5.25
WINDOW_2_BUDGET = 9.6

df_activations["total_spend"] = (
    df_activations["w1"] * WINDOW_1_BUDGET
    + df_activations["w2"] * WINDOW_2_BUDGET
)
```

```python
8/28
```

```python
df_activations_recent = df_activations[df_activations["year"] >= 1998]
# adding one year to account for 2025
# total_years = len(df_activations_recent) + 1
total_years = len(df_activations_recent) + 0
```

```python
df_activations_recent
```

```python
w1_rp = (total_years + 1) / df_activations_recent["w1"].sum()
w2_rp = (total_years + 1) / df_activations_recent["w2"].sum()
any_rp = (total_years + 1) / (df_activations_recent["any"].sum())

total_spend = df_activations_recent["total_spend"].sum()
avg_spend = total_spend / total_years
avg_spend_activation = total_spend / df_activations_recent["any"].sum()
total_budget = WINDOW_1_BUDGET + WINDOW_2_BUDGET
rp_eff = total_budget / avg_spend

print(f"window 1 RP: {w1_rp:.1f}")
print(f"window 1 prob: {1/w1_rp:.0%}")

print(f"window 2 RP: {w2_rp:.1f}")
print(f"window 2 prob: {1/w2_rp:.0%}")

print(f"any RP: {any_rp:.1f}")
print(f"any prob: {1/any_rp:.0%}")

print(f"average spend: {avg_spend:.1f}")
print(f"rp eff: {rp_eff:.1f}")
print(f"prob eff: {1/rp_eff:.0%}")
print(f"average spend per act.: {avg_spend_activation:.1f}")
```

```python
df_activations_recent[df_activations_recent["w1"]].sort_values("year")[
    "year"
].to_list()
```

```python
df_activations_recent[df_activations_recent["w2"]].sort_values("year")[
    "year"
].to_list()
```

### Iterate over percentile thresholds

```python
def calc_number_years(thresh, min_year=1998):
    df_rp, df_activations = calculate_activations(ind_frac=thresh)
    df_activations["total_spend"] = (
        df_activations["w1"] * WINDOW_1_BUDGET
        + df_activations["w2"] * WINDOW_2_BUDGET
    )
    df_activations_recent = df_activations[df_activations["year"] >= min_year]

    # adding one year to account for 2025
    total_years = len(df_activations_recent) + 1
    # w1_rp = (total_years + 1) / df_activations_recent["w1"].sum()
    # w2_rp = (total_years + 1) / df_activations_recent["w2"].sum()
    any_rp = (total_years + 1) / (df_activations_recent["any"].sum())
    any_rp_high = (total_years + 1) / (df_activations_recent["any"].sum() - 1)
    any_rp_low = (total_years + 1) / (df_activations_recent["any"].sum() + 1)

    # total_spend = df_activations_recent["total_spend"].sum()
    # avg_spend = total_spend / total_years
    # avg_spend_activation = total_spend / df_activations_recent["any"].sum()
    # total_budget = WINDOW_1_BUDGET + WINDOW_2_BUDGET
    # rp_eff = total_budget / avg_spend
    return any_rp, any_rp_high, any_rp_low
```

```python
dicts = []
for thresh in np.arange(0.1, 0.4, 0.001):
    any_rp, any_rp_high, any_rp_low = calc_number_years(thresh)
    dicts.append(
        {
            "thresh": thresh,
            "any_rp": any_rp,
            "any_rp_high": any_rp_high,
            "any_rp_low": any_rp_low,
        }
    )
```

```python
df_rps = pd.DataFrame(dicts)
```

```python
df_rps["thresh"]
```

```python
df_rps[df_rps["thresh"].round(3) == 0.201]
```

```python
fig, ax = plt.subplots(dpi=200)
df_rps.plot(x="thresh", y="any_rp", ax=ax, color="dodgerblue", legend=False)
ax.fill_between(
    df_rps["thresh"],
    df_rps["any_rp_low"],
    df_rps["any_rp_high"],
    facecolor="dodgerblue",
    alpha=0.3,
)
ax.axhline(3.5, color="crimson")
ax.annotate(
    "3.5 ans\n(limite\nminimum\nCERF)",
    (df_rps["thresh"].max(), 3.5),
    va="center",
    ha="left",
    color="crimson",
)

band_handle = Patch(
    facecolor="dodgerblue",
    alpha=0.3,
    label="Incertitude\n(± 1 activation\nhistorique)",
)

ax.legend(handles=[band_handle], loc="upper right", frameon=True)

ax.set_ylim(1, 10)
ax.set_xlim(df_rps["thresh"].min(), df_rps["thresh"].max())

ax.xaxis.set_major_formatter(
    FuncFormatter(lambda x, pos: f"{int(round(x * 100))}e")
)

ax.set_xlabel("Seuil centile par mois")
ax.set_ylabel("Période de retour globale du cadre (ans)")

[ax.spines[x].set_visible(False) for x in ["top", "right"]]
```

```python
1/3.5
```

```python

```
