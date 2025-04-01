---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.1
  kernelspec:
    display_name: ds-aa-ner-drought
    language: python
    name: ds-aa-ner-drought
---

# IRI trend

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
import ocha_stratus as stratus

from src.constants import *
```

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

```python
def calculate_activations(ind_frac: float):
    df_iri = df_iri_raw.copy()
    for x in df_iri:
        if "bool" in x or x == "year":
            continue
        if x == "Aug":
            df_iri[f"{x}_bool"] = df_iri[x] <= df_iri[x].quantile(ind_frac)
        else:
            df_iri[f"{x}_bool"] = df_iri[x] >= df_iri[x].quantile(1 - ind_frac)

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

```python
ind_frac = 0.35
df_rp, df_activations = calculate_activations(ind_frac=ind_frac)
plot_rp(df_rp, ind_frac)
```

```python
df_rp
```

```python
ind_frac = 0.3
df_rp, df_activations = calculate_activations(ind_frac=ind_frac)
plot_rp(df_rp, ind_frac)
```

```python

```
