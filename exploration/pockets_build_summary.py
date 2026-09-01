"""Combine the fetched indicators into per-unit 2026 return-period tables.

Return-period convention (team standard, Weibull plotting position, as in
the rolling-threshold analysis): rank the 2026 value among ALL years of the
indicator's record including 2026 (rank 1 = most drought-like), then
RP = (n + 1) / rank. RP is capped conceptually by record length — a value
of (n+1)/1 just means "worst on record".

Outputs (exploration/public/pockets/):
- ``summary_adm2.csv`` — one row per department: each indicator's 2026
  value, dry rank, record length and RP; HNRP severity/PiN; convergence
  count of indicators at RP >= 5.
- ``summary_adm1.csv`` — same for regions plus ASI/VHI (adm1-only) and the
  SEAS5 adm1 stats.
- ``gauges_summary.csv`` — per station: Jun+Jul 2026 total, rank/RP within
  the OGIMET CLIMAT record, and the DMN-transmitted WMO quintile codes.

Usage: ``uv run python exploration/pockets_build_summary.py``
"""

from pathlib import Path

import numpy as np
import ocha_stratus as stratus
import pandas as pd

D = Path(__file__).parent / "public" / "pockets"

# latest complete ASIS dekad at analysis time (11-20 Aug 2026)
ASIS_DEKAD = ("08", 2)
SEAS5_SKILL_MIN_R = 0.30  # below this, SEAS5 is not shown (no-skill mask)
CONVERGENCE_RP = 5.0

# WMO-id -> (lat, lon), from NOAA ISD station history; fallback where the
# OGIMET coordinate scrape comes back empty
STATION_COORDS = {
    "61017": (18.683, 12.917),  # Bilma
    "61024": (16.967, 7.967),  # Agadez
    "61036": (14.200, 1.450),  # Tillabery
    "61043": (14.876, 5.265),  # Tahoua
    "61045": (13.983, 10.300),  # Goure
    "61049": (14.250, 13.117),  # N'Guigmi
    "61052": (13.482, 2.184),  # Niamey-Aero (Diori Hamani)
    "61053": (13.033, 3.300),  # Dosso
    "61075": (13.800, 5.250),  # Birni-N'Konni
    "61080": (13.503, 7.127),  # Maradi
    "61085": (13.373, 12.627),  # Diffa
    "61090": (13.779, 8.984),  # Zinder
    "61091": (12.983, 8.933),  # Magaria
    "61096": (13.233, 11.983),  # Maine-Soroa
    "61099": (11.883, 3.450),  # Gaya
}


def dry_rank_rp(series_by_year, year=2026, lower_is_worse=True):
    """(value, rank, n, rp) of `year` within its full record."""
    s = series_by_year.dropna()
    if year not in s.index:
        return np.nan, np.nan, len(s), np.nan
    v = s.loc[year]
    if lower_is_worse:
        rank = int((s < v).sum()) + 1
    else:
        rank = int((s > v).sum()) + 1
    n = len(s)
    return float(v), rank, n, (n + 1) / rank


def rp_table(df, value_col, unit_col="pcode", lower_is_worse=True):
    rows = []
    for unit, g in df.groupby(unit_col):
        s = g.set_index("year")[value_col]
        v, rank, n, rp = dry_rank_rp(s, lower_is_worse=lower_is_worse)
        rows.append(
            {unit_col: unit, "value": v, "rank": rank, "n": n, "rp": rp}
        )
    return pd.DataFrame(rows)


def load_asis(fname, value_name):
    df = pd.read_csv(D / fname)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%m")
    df["Dekad"] = df["Date"].dt.day.map({1: 1, 11: 2, 21: 3})
    df["Year"] = df["Date"].dt.year
    sel = df[(df["Month"] == ASIS_DEKAD[0]) & (df["Dekad"] == ASIS_DEKAD[1])]
    out = sel.rename(columns={"Province": "region", "Data": value_name})[
        ["region", "Year", value_name]
    ].rename(columns={"Year": "year"})
    return out


def main():
    adm2_names = pd.read_csv(D / "hnrp_2026_adm2.csv")
    adm2_names["pcode"] = adm2_names["admin2_code"].str.replace(
        "NER", "NE", regex=False
    )

    # --- rainfall indicators per adm2
    chirps = pd.read_csv(D / "chirps_junjul_adm2.csv")
    t_chirps = rp_table(chirps, "junjul_mm").add_prefix("chirps_")

    imerg = pd.read_csv(D / "imerg_junaug_adm2.csv")
    # normalize for small day gaps (2026 has 90 of 91 days)
    imerg["junaug_mm"] = imerg["junaug_mm"] * 91 / imerg["n_days"]
    t_imerg = rp_table(imerg, "junaug_mm").add_prefix("imerg_")

    era5 = pd.read_csv(D / "era5_junjul_adm2.csv")
    t_era5 = rp_table(era5, "junjul_mm").add_prefix("era5_")

    # --- SEAS5 (issued Aug 2026), computed by pockets_fetch_seas5.py
    seas5 = pd.read_csv(D / "seas5_skill_ner.csv")
    s2 = seas5[seas5["adm_level"] == 2]

    def seas5_cols(trim, prefix):
        # displayed values are the DETRENDED variant (both sides detrended
        # in log space, the skill explorer's "Detrended" mode); the raw
        # variant is kept alongside with a _raw suffix
        t = s2[s2["trimester"] == trim][
            [
                "pcode",
                "pearson_r_dt",
                "forecast_percentile_dt",
                "forecast_rp_dt",
                "pearson_r",
                "forecast_percentile",
                "forecast_rp",
            ]
        ]
        return t.rename(
            columns={
                "pearson_r_dt": f"{prefix}_r",
                "forecast_percentile_dt": f"{prefix}_pctile",
                "forecast_rp_dt": f"{prefix}_rp",
                "pearson_r": f"{prefix}_raw_r",
                "forecast_percentile": f"{prefix}_raw_pctile",
                "forecast_rp": f"{prefix}_raw_rp",
            }
        )

    # --- vegetation per adm1 (FAO ASIS regions)
    asi = load_asis("asi_dekad.csv", "asi")
    vhi = load_asis("vhi_dekad.csv", "vhi")
    t_asi = rp_table(asi, "asi", unit_col="region", lower_is_worse=False)
    t_asi = t_asi.add_prefix("asi_").rename(columns={"asi_region": "region"})
    t_vhi = rp_table(vhi, "vhi", unit_col="region", lower_is_worse=True)
    t_vhi = t_vhi.add_prefix("vhi_").rename(columns={"vhi_region": "region"})

    # ASIS region name -> ADM1 pcode (CODAB French names)
    region_to_adm1 = {
        "Agadez": "NE001",
        "Diffa": "NE002",
        "Dosso": "NE003",
        "Maradi": "NE004",
        "Tahoua": "NE005",
        "Tillaberi": "NE006",
        "Zinder": "NE007",
        "Niamey": "NE008",
    }
    veg = t_asi.merge(t_vhi, on="region")
    veg["adm1_pcode"] = veg["region"].map(region_to_adm1)

    # --- ENACTS MON Jun-Jul SPI per department (IRI Maproom export API);
    # the framework's own observational indicator, 1991-2026. Northern
    # desert departments have no ENACTS coverage (absent here).
    enacts = pd.read_csv(D / "enacts_spi_adm.csv", dtype={"level": str})
    e2 = enacts[enacts["level"] == "2"][["pcode", "year", "spi"]]
    t_enacts = rp_table(e2, "spi").add_prefix("enacts_")

    # --- assemble adm2 summary
    out = adm2_names[
        [
            "pcode",
            "admin1_name",
            "admin2_name",
            "population",
            "final_severity",
            "final_pin",
        ]
    ].copy()
    out["adm1_pcode"] = out["pcode"].str[:5]
    for t, key in [
        (t_chirps, "chirps_pcode"),
        (t_imerg, "imerg_pcode"),
        (t_era5, "era5_pcode"),
        (t_enacts, "enacts_pcode"),
    ]:
        out = out.merge(
            t.rename(columns={key: "pcode"}), on="pcode", how="left"
        )
    out = out.merge(seas5_cols("JAS", "seas5_jas"), on="pcode", how="left")
    out = out.merge(seas5_cols("ASO", "seas5_aso"), on="pcode", how="left")
    out = out.merge(
        veg[
            [
                "adm1_pcode",
                "asi_value",
                "asi_rank",
                "asi_n",
                "asi_rp",
                "vhi_value",
                "vhi_rank",
                "vhi_n",
                "vhi_rp",
            ]
        ],
        on="adm1_pcode",
        how="left",
    )

    # skill mask: hide SEAS5 columns where the detrended r < threshold
    for p in ("seas5_jas", "seas5_aso"):
        low = out[f"{p}_r"] < SEAS5_SKILL_MIN_R
        out.loc[low, [f"{p}_pctile", f"{p}_rp"]] = np.nan

    # convergence: how many of the five indicators are at RP >= 5
    # (CHIRPS Jun-Jul, IMERG Jun-Aug, ENACTS MON Jun-Jul SPI, skill-filtered
    # SEAS5+ERA5 JAS hybrid (detrended), vegetation = worst of regional
    # ASI/VHI). The rainfall witnesses are kept separate: different sensors,
    # windows and gauge inputs, and they disagree regionally in 2026.
    out["rain_rp"] = out[["chirps_rp", "imerg_rp"]].max(axis=1)
    out["veg_rp"] = out[["asi_rp", "vhi_rp"]].max(axis=1)
    out["conv_n"] = (
        (out["chirps_rp"] >= CONVERGENCE_RP).astype(int)
        + (out["imerg_rp"] >= CONVERGENCE_RP).astype(int)
        + (out["enacts_rp"] >= CONVERGENCE_RP).fillna(False).astype(int)
        + (out["veg_rp"] >= CONVERGENCE_RP).astype(int)
        + (out["seas5_jas_rp"] >= CONVERGENCE_RP).fillna(False).astype(int)
    )
    out.to_csv(D / "summary_adm2.csv", index=False)

    # --- adm1 summary
    s1 = seas5[seas5["adm_level"] == 1]
    chirps_adm1 = chirps.assign(adm1=chirps["pcode"].str[:5])
    # population-free spatial mean: average of member adm2 zonal means is fine
    # at this scale, but recompute from pixels would be better; keep simple.
    c1 = (
        chirps_adm1.groupby(["adm1", "year"])["junjul_mm"].mean().reset_index()
    )
    t_c1 = rp_table(c1.rename(columns={"adm1": "pcode"}), "junjul_mm")
    t_c1 = t_c1.add_prefix("chirps_")
    adm1 = veg.merge(
        t_c1.rename(columns={"chirps_pcode": "adm1_pcode"}),
        on="adm1_pcode",
        how="left",
    )
    for trim, prefix in [("JAS", "seas5_jas"), ("ASO", "seas5_aso")]:
        t = s1[s1["trimester"] == trim][
            ["pcode", "pearson_r", "forecast_percentile", "forecast_rp"]
        ].rename(
            columns={
                "pcode": "adm1_pcode",
                "pearson_r": f"{prefix}_r",
                "forecast_percentile": f"{prefix}_pctile",
                "forecast_rp": f"{prefix}_rp",
            }
        )
        adm1 = adm1.merge(t, on="adm1_pcode", how="left")
    adm1.to_csv(D / "summary_adm1.csv", index=False)

    # --- gauges
    g = pd.read_csv(D / "gauges_monthly.csv", dtype={"wmo_id": str})
    # Diffa's July 2026 CLIMAT transmits 447 mm in 4 rain days — contradicted
    # by the station's own synop reports (~27 mm), by CHIRPS at the town
    # (~88 mm, with Diffa gauges ingested by CHC), and by every other 2026
    # drought signal in the department. Treated as a transmission error and
    # excluded from the ranking (kept in gauges_monthly.csv).
    bad = (g["wmo_id"] == "61085") & (g["year"] == 2026) & (g["month"] == 7)
    g = g[~bad]
    # Gaya's June 2026 report (163 mm — jointly the wettest June of its own
    # archive) was NOT ingested by CHC's station screening for CHIRPS
    # (absent from global.stationsUsed.2026.06.csv; the July report was
    # accepted), and sits well above the CHIRPS pixel at the town (131 mm,
    # at its median). Its July (121 mm, ~35% below the pixel's climatology)
    # corroborates the dryness. The near-normal seasonal total therefore
    # rests entirely on the suspect June value: kept, but flagged.
    GAUGE_FLAGS = {"61099": "jun2026_suspect"}
    if "lat" not in g or g["lat"].isna().all():
        g["lat"] = g["wmo_id"].map(
            lambda i: STATION_COORDS.get(i, (np.nan,))[0]
        )
        g["lon"] = g["wmo_id"].map(
            lambda i: STATION_COORDS.get(i, (np.nan, np.nan))[1]
        )
    else:
        g["lat"] = g["lat"].fillna(
            g["wmo_id"].map(lambda i: STATION_COORDS.get(i, (np.nan,))[0])
        )
        g["lon"] = g["lon"].fillna(
            g["wmo_id"].map(
                lambda i: STATION_COORDS.get(i, (np.nan, np.nan))[1]
            )
        )
    jj = (
        g[g["month"].isin([6, 7])]
        .groupby(["wmo_id", "name", "year"])
        .agg(
            junjul_mm=("precip_mm", "sum"),
            n_months=("precip_mm", "size"),
            lat=("lat", "first"),
            lon=("lon", "first"),
        )
        .reset_index()
    )
    jj = jj[jj["n_months"] == 2]
    rows = []
    for (wmo_id, name), gg in jj.groupby(["wmo_id", "name"]):
        s = gg.set_index("year")["junjul_mm"]
        v, rank, n, rp = dry_rank_rp(s)
        q26 = g[(g["wmo_id"] == wmo_id) & (g["year"] == 2026)].set_index(
            "month"
        )["quintile"]
        aug26 = g[
            (g["wmo_id"] == wmo_id) & (g["year"] == 2026) & (g["month"] == 8)
        ]["precip_mm"]
        rows.append(
            {
                "wmo_id": wmo_id,
                "name": name,
                "lat": gg["lat"].iloc[0],
                "lon": gg["lon"].iloc[0],
                "junjul_2026_mm": v,
                "rank": rank,
                "n_years": n,
                "rp": rp,
                "q_jun": q26.get(6, np.nan),
                "q_jul": q26.get(7, np.nan),
                "q_aug": q26.get(8, np.nan),
                "aug_2026_mm": aug26.iloc[0] if len(aug26) else np.nan,
                "flag": GAUGE_FLAGS.get(wmo_id),
            }
        )
    pd.DataFrame(rows).to_csv(D / "gauges_summary.csv", index=False)

    for name in ("summary_adm2", "summary_adm1", "gauges_summary"):
        stratus.upload_csv_to_blob(
            pd.read_csv(D / f"{name}.csv"),
            f"ds-aa-ner-drought/processed/pockets/{name}.csv",
            stage="dev",
        )
    print("wrote summary_adm2 / summary_adm1 / gauges_summary (+ blob copies)")


if __name__ == "__main__":
    main()
