"""Render the bilingual static 2026 drought-pockets page.

Reads the summaries produced by ``pockets_build_summary.py`` (which itself
consumes the ``pockets_fetch_*`` outputs), renders all maps via
``pockets_figures.py``, and writes a self-contained
``docs/pockets/index.html`` (figures embedded as base64 PNGs).

Every fixed UI string is emitted in English AND French; a client-side
toggle (the team's D86 mechanism: dual spans + ``localStorage['aa-lang']``)
switches the visible language.

Usage: ``uv run python exploration/pockets_page.py``
"""

import base64
import html as html_mod
from pathlib import Path

import numpy as np
import pandas as pd
import pockets_figures as figs

D = Path(__file__).parent / "public" / "pockets"
OUT = Path(__file__).parent.parent / "docs" / "pockets" / "index.html"

ANALYSIS_DATE_EN = "1 September 2026"
ANALYSIS_DATE_FR = "1ᵉʳ septembre 2026"


def T(en, fr):
    """Dual-language span pair, CSS-switched."""
    return (
        f'<span class="lv lv-en">{en}</span>'
        f'<span class="lv lv-fr">{fr}</span>'
    )


def fmt_rp(v):
    if pd.isna(v):
        return "–"
    if v >= 10:
        return f"{v:.0f}"
    return f"{v:.1f}"


def rp_cell(v):
    if pd.isna(v):
        return '<td class="na">–</td>'
    cls = int(np.digitize(v, figs.RP_BINS[1:-1]))
    color = figs.RP_COLORS[cls]
    dark = " dark" if cls >= 3 else ""
    return f'<td class="rp{dark}" style="background:{color}">{fmt_rp(v)}</td>'


def sev_cell(v):
    if pd.isna(v):
        return '<td class="na">–</td>'
    v = int(v)
    color = figs.SEV_COLORS.get(v, "#eeeeee")
    dark = " dark" if v >= 4 else ""
    return f'<td class="rp{dark}" style="background:{color}">{v}</td>'


def main():
    summary = pd.read_csv(D / "summary_adm2.csv")
    gauges = pd.read_csv(D / "gauges_summary.csv", dtype={"wmo_id": str})

    # vegetation history for strip plots
    asi = figs.pd.read_csv(D / "asi_dekad.csv")
    vhi = figs.pd.read_csv(D / "vhi_dekad.csv")
    for df in (asi, vhi):
        df.columns = [c.strip() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"])

    def dekad_series(df):
        sel = df[(df["Date"].dt.month == 8) & (df["Date"].dt.day == 11)]
        return sel.rename(columns={"Province": "region", "Data": "v"}).assign(
            year=sel["Date"].dt.year
        )[["region", "year", "v"]]

    asi_h = dekad_series(asi)
    vhi_h = dekad_series(vhi)

    print("rendering figures…", flush=True)
    img_conv = figs.fig_convergence(summary)
    img_pixel = figs.fig_pixel_percentile()
    img_rain = figs.fig_rain_rp_trio(summary)
    img_gauge = figs.fig_gauge_map(gauges)
    img_veg = figs.fig_veg_strips(asi_h, vhi_h)
    img_seas5 = figs.fig_seas5_pair(summary)
    img_hnrp = figs.fig_hnrp(summary)
    fao_ndvi = base64.b64encode(
        (D / "fao_ndvi_anom_map.png").read_bytes()
    ).decode()
    fao_asi = base64.b64encode((D / "fao_asi_map.png").read_bytes()).decode()

    # ---- dynamic narrative numbers
    n_rp5_chirps = int((summary["chirps_rp"] >= 5).sum())
    n_rp5_imerg = int((summary["imerg_rp"] >= 5).sum())
    sev4 = summary[summary["final_severity"] >= 4]

    # flagged table: any signal at RP>=5 or severity>=4
    flag = summary[
        (
            summary[
                [
                    "chirps_rp",
                    "imerg_rp",
                    "enacts_rp",
                    "seas5_jas_rp",
                    "veg_rp",
                ]
            ]
            >= 5
        ).any(axis=1)
        | (summary["final_severity"] >= 4)
    ].copy()
    flag = flag.sort_values(["conv_n", "rain_rp"], ascending=[False, False])

    def flag_rows():
        out = []
        for _, r in flag.iterrows():
            out.append(
                "<tr>"
                f"<td>{html_mod.escape(str(r['admin2_name']))}</td>"
                f"<td>{html_mod.escape(str(r['admin1_name']))}</td>"
                + rp_cell(r["chirps_rp"])
                + rp_cell(r["imerg_rp"])
                + rp_cell(r["enacts_rp"])
                + rp_cell(r["seas5_jas_rp"])
                + rp_cell(r["asi_rp"])
                + rp_cell(r["vhi_rp"])
                + sev_cell(r["final_severity"])
                + f"<td>{'' if pd.isna(r['final_pin']) else format(int(r['final_pin']), ',')}</td>"
                f"<td><b>{int(r['conv_n'])}</b></td>"
                "</tr>"
            )
        return "\n".join(out)

    def gauge_rows():
        out = []
        for _, r in gauges.sort_values("rp", ascending=False).iterrows():
            mm26 = (
                "–"
                if pd.isna(r["junjul_2026_mm"])
                else f"{r['junjul_2026_mm']:.0f}"
            )
            rank = (
                "–"
                if pd.isna(r["rank"])
                else f"{int(r['rank'])}/{int(r['n_years'])}"
            )
            out.append(
                "<tr>"
                f"<td>{html_mod.escape(r['name'])} ({r['wmo_id']})</td>"
                f"<td>{mm26}</td>"
                f"<td>{rank}</td>" + rp_cell(r["rp"]) + "</tr>"
            )
        return "\n".join(out)

    sev4_names = ", ".join(
        f"{r['admin2_name']} ({r['admin1_name']})" for _, r in sev4.iterrows()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Niger 2026 — pockets of drought</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a; background: #ffffff;
    margin: 0; padding: 1rem 1rem 4rem;
    line-height: 1.55;
  }}
  main {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 1.7rem; margin-bottom: 0.3rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 2.6rem;
       border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; }}
  figure {{ margin: 1.2rem 0; text-align: center; }}
  figure img {{ max-width: 100%; height: auto; }}
  figcaption {{ color: #555; font-size: 0.85rem; margin-top: 0.4rem;
               text-align: left; }}
  table {{ border-collapse: collapse; margin: 1rem 0; font-size: 0.85rem; }}
  .tablewrap {{ overflow-x: auto; }}
  th, td {{ border: 1px solid #d9d9d9; padding: 0.35rem 0.55rem;
           text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  td.rp {{ text-align: center; font-weight: 600; }}
  td.rp.dark {{ color: #ffffff; }}
  td.na {{ text-align: center; color: #999; }}
  .callout {{ background: #fff8e6; border-left: 4px solid #e6a700;
             padding: 0.6rem 1rem; margin: 1rem 0; }}
  .findings {{ background: #f2f7fb; border-left: 4px solid #2a6fb0;
              padding: 0.6rem 1rem; margin: 1rem 0; }}
  .note {{ color: #555; font-size: 0.85rem; font-style: italic; }}
  code {{ background: #f2f2f2; padding: 0.1rem 0.3rem; border-radius: 3px;
         font-size: 0.85em; }}
  footer {{ margin-top: 3rem; color: #777; font-size: 0.8rem; }}
  .home-link {{ display:inline-block; margin: 0 0 0.8rem; padding:6px 12px;
    font-size: 0.8rem; color:#1e795f; background:#e9f5f1;
    border:1px solid #d4eae4; border-radius:4px; text-decoration:none; }}
  /* --- language toggle (team D86 mechanism) --- */
  .lv {{ display: none; }}
  html[data-lang="en"] .lv-en {{ display: inline; }}
  html[data-lang="fr"] .lv-fr {{ display: inline; }}
  html:not([data-lang]) .lv-en {{ display: inline; }}
  .lang-toggle {{ float: right; margin-top: 0.2rem; }}
  .lang-toggle button {{
    border: 1px solid #ccc; background: #fff; padding: 3px 10px;
    cursor: pointer; font-size: 0.8rem; }}
  .lang-toggle button.active {{ background: #2a6fb0; color: #fff;
    border-color: #2a6fb0; }}
</style>
</head>
<body>
<main>
<div class="lang-toggle">
  <button id="btn-en" onclick="aaSetLang('en')">EN</button>
  <button id="btn-fr" onclick="aaSetLang('fr')">FR</button>
</div>
<a class="home-link" href="../">{T("← Niger drought AA — trigger explorer",
                                   "← AA sécheresse Niger — explorateur du déclencheur")}</a>

<h1>{T("Niger 2026 — pockets of drought", "Niger 2026 — poches de sécheresse")}</h1>
<p class="note">{T(
    f"Analysis of {ANALYSIS_DATE_EN}, covering the June–September rainy season. "
    "OCHA Centre for Humanitarian Data.",
    f"Analyse du {ANALYSIS_DATE_FR}, couvrant la saison des pluies de juin à "
    "septembre. Centre de données humanitaires de l’OCHA.")}</p>

<p>{T(
    "This page looks for areas of Niger where drought could be emerging in the "
    "2026 season, by putting this year's observed rainfall (gridded products, "
    "the DMN's ENACTS analysis and rain gauges), "
    "vegetation stress (FAO ASI and the NDVI-based VHI) and "
    "the current skill-filtered SEAS5 seasonal forecast in the context of each "
    "indicator's own multi-decade record. Every indicator is expressed as an "
    "empirical return period (RP): a department at RP 10 is seeing a value "
    "that dry roughly once in 10 years. Humanitarian-needs severity from the "
    "2026 HNRP is overlaid to show where climate signals coincide with the "
    "highest pre-existing needs.",
    "Cette page recherche les zones du Niger où une sécheresse pourrait se "
    "dessiner pendant la saison 2026, en replaçant les précipitations "
    "observées cette année (produits maillés, analyse ENACTS de la DMN et "
    "pluviomètres), le "
    "stress de la végétation (ASI de la FAO et VHI, dérivé du NDVI) et la "
    "prévision saisonnière SEAS5 filtrée selon la performance du modèle, "
    "dans le contexte de plusieurs décennies d’historique pour chaque "
    "indicateur. Chaque indicateur est exprimé en période de retour "
    "empirique (PR)&nbsp;: un département à PR&nbsp;10 connaît une valeur "
    "aussi sèche environ une fois tous les 10&nbsp;ans. La sévérité des "
    "besoins humanitaires du HNRP 2026 est superposée pour montrer où les "
    "signaux climatiques coïncident avec les besoins préexistants les plus "
    "élevés.")}</p>

<div class="findings">
<b>{T("Key findings", "Principaux constats")}</b>
<ul>
<li>{T(
  f"Rainfall deficits are widespread: {n_rp5_chirps} of 67 departments are at "
  "a ≥ 5-year return period for June–July rainfall (CHIRPS, 1981–2026), and "
  f"{n_rp5_imerg} of 67 for June–August rainfall (IMERG, 1998–2026).",
  f"Les déficits pluviométriques sont étendus&nbsp;: {n_rp5_chirps} des 67 "
  "départements sont à une période de retour ≥ 5&nbsp;ans pour les "
  "précipitations de juin–juillet (CHIRPS, 1981–2026), et "
  f"{n_rp5_imerg} sur 67 pour juin–août (IMERG, 1998–2026).")}</li>
<li>{T(
  "ENACTS — the DMN analysis behind the framework's observational "
  "trigger, here pulled per department from the IRI Maproom — reads "
  "−0.12 over the monitored zone (no trigger, threshold −0.71), yet its "
  "own department detail shows RP ≥ 5 pockets in eastern Diffa "
  "(Maïné-Soroa, N'Gourti) and southern Dosso (Dioundiou SPI −1.3, RP 9; "
  "Gaya −1.0). Being gauge-anchored, it reads the Tahoua belt as "
  "near-normal, like the town gauges — where satellite and reanalysis "
  "products are severe.",
  "ENACTS — l’analyse de la DMN derrière le déclencheur observationnel "
  "du cadre, extraite ici par département depuis le Maproom de l’IRI — "
  "vaut −0,12 sur la zone suivie (seuil de −0,71 non atteint), mais son "
  "propre détail départemental montre des poches à PR ≥ 5 dans l’est de "
  "Diffa (Maïné-Soroa, N'Gourti) et le sud de Dosso (Dioundiou SPI −1,3, "
  "PR 9&nbsp;; Gaya −1,0). Ancrée sur les pluviomètres, elle lit la bande "
  "de Tahoua comme proche de la normale, à l’image des stations en "
  "ville — là où les produits satellitaires et de réanalyse sont "
  "sévères.")}</li>
<li>{T(
  "The sharpest pocket is southern Dosso: Gaya and Dioundiou have 4 of 5 "
  "indicators at RP ≥ 5 — CHIRPS, IMERG, the DMN's own ENACTS SPI and the "
  "end-of-season hybrid all agree. Fourteen more departments are at 3 of "
  "5: the rest of Dosso region, the Tahoua belt (Illéla, Keita, Ville de "
  "Tahoua, Bouza, Bagaroua), Filingué (Tillabéri), Tanout and Tesker "
  "(Zinder) and Maïné-Soroa / N'Gourti (Diffa). A second, needs-critical "
  "pocket covers eastern Diffa (N'Guigmi, Bosso, Diffa) and western "
  "Tillabéri (Téra, Bankilaré, Torodi), driven by IMERG June–August "
  "deficits and the dry end-of-season outlook.",
  "La poche la plus nette est le sud de Dosso&nbsp;: à Gaya et Dioundiou, "
  "4 indicateurs sur 5 sont à PR ≥ 5 — CHIRPS, IMERG, le SPI ENACTS de la "
  "DMN elle-même et l’hybride de fin de saison concordent. Quatorze autres "
  "départements sont à 3 sur 5&nbsp;: le reste de la région de Dosso, la "
  "bande de Tahoua (Illéla, Keita, Ville de Tahoua, Bouza, Bagaroua), "
  "Filingué (Tillabéri), Tanout et Tesker (Zinder) et Maïné-Soroa / "
  "N'Gourti (Diffa). Une seconde poche, critique du point de vue des "
  "besoins, couvre l’est de Diffa (N'Guigmi, Bosso, Diffa) et l’ouest de "
  "Tillabéri (Téra, Bankilaré, Torodi), portée par les déficits IMERG de "
  "juin–août et la perspective sèche de fin de saison.")}</li>
<li>{T(
  "Vegetation stress is, so far, milder than the rainfall deficits: no "
  "region's ASI or VHI has crossed a 5-year return period at the 11–20 "
  "August dekad. Diffa is closest (ASI 16% of cropland stressed, 9th worst "
  "of 43 years) and FAO's NDVI-anomaly map shows below-normal vegetation "
  "along the southern agricultural belt and the far south-east.",
  "Le stress de la végétation reste, à ce stade, plus modéré que les "
  "déficits pluviométriques&nbsp;: aucune région n’a franchi une période "
  "de retour de 5&nbsp;ans en ASI ou VHI à la décade du 11–20 août. Diffa "
  "en est la plus proche (ASI&nbsp;: 16&nbsp;% des cultures stressées, "
  "9ᵉ pire valeur sur 43&nbsp;ans) et la carte d’anomalie de NDVI de la "
  "FAO montre une végétation sous la normale le long de la bande agricole "
  "sud et à l’extrême sud-est.")}</li>
<li>{T(
  "The end-of-season outlook — the SEAS5+ERA5 hybrid for JAS (July from "
  "ERA5, August–September from the August SEAS5 issuance), detrended and "
  "normalized as usual — is severely dry over almost the whole "
  "agricultural south: relative to the trend-adjusted record, Dosso and "
  "Maradi regions have their driest JAS hybrid of 46 years, and "
  "Tillabéri, Niamey and Diffa sit near the 2nd percentile (RP ≈ 23), "
  "with strong historical performance (r 0.63–0.82). Only Agadez is "
  "moderate. Note the hybrid's July leg inherits ERA5's pronounced 2026 "
  "dry anomaly.",
  "La perspective de fin de saison — l’hybride SEAS5+ERA5 pour JAS "
  "(juillet d’ERA5, août–septembre de l’émission SEAS5 d’août), détendancé "
  "et normalisé comme d’habitude — est sévèrement sèche sur presque tout "
  "le sud agricole&nbsp;: par rapport à l’historique corrigé de la "
  "tendance, les régions de Dosso et de Maradi connaissent leur hybride "
  "JAS le plus sec en 46&nbsp;ans, et Tillabéri, Niamey et Diffa se "
  "situent près du 2ᵉ percentile (PR ≈ 23), avec une forte performance "
  "historique (r de 0,63 à 0,82). Seul Agadez reste modéré. Noter que le "
  "volet juillet de l’hybride hérite de l’anomalie sèche marquée d’ERA5 "
  "en 2026.")}</li>
<li>{T(
  f"{len(sev4)} departments hold the highest HNRP intersectoral severity "
  f"(class 4): {sev4_names}. All four also show at least one drought signal "
  "at RP ≥ 5 in 2026.",
  f"{len(sev4)} départements présentent la sévérité intersectorielle la plus "
  f"élevée du HNRP (classe 4)&nbsp;: {sev4_names}. Tous quatre montrent "
  "aussi au moins un signal de sécheresse à PR ≥ 5 en 2026.")}</li>
</ul>
</div>

<h2>{T("Where the signals converge", "Où les signaux convergent")}</h2>
<p>{T(
  "The map counts how many of five indicators are at a ≥ 5-year return "
  "period in each department: CHIRPS June–July rainfall, IMERG June–August "
  "rainfall, the ENACTS June–July SPI, the skill-filtered SEAS5+ERA5 "
  "end-of-season hybrid (JAS, detrended), and regional vegetation (worst "
  "of ASI / VHI). The indicators are related but not redundant — the "
  "rainfall witnesses use different sensors, windows and gauge inputs, and "
  "they disagree regionally in 2026. Hatching marks the four departments "
  "in HNRP severity class 4.",
  "La carte compte, pour chaque département, combien de cinq indicateurs "
  "sont à une période de retour ≥ 5&nbsp;ans&nbsp;: précipitations CHIRPS "
  "juin–juillet, précipitations IMERG juin–août, SPI juin–juillet ENACTS, "
  "hybride SEAS5+ERA5 de fin de saison filtré selon la performance (JAS, "
  "détendancé), et végétation régionale (pire de l’ASI / du VHI). Les "
  "indicateurs sont liés mais non redondants — les témoins pluviométriques "
  "reposent sur des capteurs, des fenêtres et des intrants pluviométriques "
  "différents, et divergent régionalement en 2026. Les hachures marquent "
  "les quatre départements en classe de sévérité 4 du HNRP.")}</p>
<figure>
<img src="data:image/png;base64,{img_conv}" alt="Convergence map">
<figcaption>{T(
  "Number of indicators (0–5) at return period ≥ 5 years, by department; "
  "hatched: HNRP 2026 intersectoral severity 4.",
  "Nombre d’indicateurs (0–5) à une période de retour ≥ 5 ans, par "
  "département&nbsp;; hachures&nbsp;: sévérité intersectorielle 4 du "
  "HNRP 2026.")}</figcaption>
</figure>

<div class="tablewrap">
<table>
<tr>
  <th>{T("Department", "Département")}</th>
  <th>{T("Region", "Région")}</th>
  <th>{T("CHIRPS Jun–Jul RP", "CHIRPS juin–juil. PR")}</th>
  <th>{T("IMERG Jun–Aug RP", "IMERG juin–août PR")}</th>
  <th>{T("ENACTS SPI RP", "ENACTS SPI PR")}</th>
  <th>{T("SEAS5 JAS RP", "SEAS5 JAS PR")}</th>
  <th>{T("ASI RP*", "ASI PR*")}</th>
  <th>{T("VHI RP*", "VHI PR*")}</th>
  <th>{T("HNRP severity", "Sévérité HNRP")}</th>
  <th>{T("People in need", "Personnes dans le besoin")}</th>
  <th>{T("Convergence", "Convergence")}</th>
</tr>
{flag_rows()}
</table>
</div>
<p class="note">{T(
  "Departments with at least one indicator at RP ≥ 5 or HNRP severity 4. "
  "* ASI/VHI are only available per region (FAO GAUL admin-1); the regional "
  "value is shown for each department. ENACTS is blank for Saharan "
  "departments without coverage. SEAS5 (the detrended SEAS5+ERA5 JAS "
  "hybrid) is blank where the model has insufficient historical "
  "performance (r < 0.30).",
  "Départements avec au moins un indicateur à PR ≥ 5 ou en sévérité 4 du "
  "HNRP. * L’ASI et le VHI ne sont disponibles que par région (admin-1 GAUL "
  "de la FAO)&nbsp;; la valeur régionale est reprise pour chaque "
  "département. ENACTS est vide pour les départements sahariens sans "
  "couverture. SEAS5 (l’hybride SEAS5+ERA5 JAS détendancé) est vide "
  "lorsque la performance historique du modèle est insuffisante "
  "(r &lt; 0,30).")}</p>

<h2>{T("Observed rainfall — CHIRPS, IMERG and ENACTS",
       "Précipitations observées — CHIRPS, IMERG et ENACTS")}</h2>
<p>{T(
  "Three witnesses of the season so far, each shown rather than averaged. "
  "CHIRPS (gauge-calibrated satellite, 1981–2026, final product through "
  "July) is driest over the Tahoua–Dosso belt; IMERG (satellite-only, "
  "1998–2026, through 30 August) is driest over eastern Diffa and western "
  "Tillabéri; and ENACTS — the DMN's own gauge + satellite analysis behind "
  "the framework's observational trigger, pulled per department from the "
  "IRI Maproom (June–July SPI, 1991–2026) — flags eastern Diffa "
  "(Maïné-Soroa, N'Gourti) and southern Dosso (Dioundiou SPI −1.3, Gaya "
  "−1.0) while reading the Tahoua belt as near-normal. Over the monitored "
  "zone as a whole ENACTS reads −0.12 — far from the −0.71 trigger "
  "threshold — even though its own department detail contains 1-in-5 to "
  "1-in-9-year pockets.",
  "Trois témoins de la saison à ce stade, montrés côte à côte plutôt que "
  "moyennés. CHIRPS (satellite calé sur les pluviomètres, 1981–2026, "
  "produit final jusqu’à juillet) est le plus sec sur la bande "
  "Tahoua–Dosso&nbsp;; IMERG (satellitaire, 1998–2026, jusqu’au 30 août) "
  "est le plus sec sur l’est de Diffa et l’ouest de Tillabéri&nbsp;; et "
  "ENACTS — l’analyse pluviomètres + satellite de la DMN qui alimente le "
  "déclencheur observationnel du cadre, extraite par département depuis le "
  "Maproom de l’IRI (SPI juin–juillet, 1991–2026) — signale l’est de Diffa "
  "(Maïné-Soroa, N'Gourti) et le sud de Dosso (Dioundiou SPI −1,3, Gaya "
  "−1,0) tout en lisant la bande de Tahoua comme proche de la normale. Sur "
  "l’ensemble de la zone suivie, ENACTS vaut −0,12 — loin du seuil de "
  "déclenchement de −0,71 — alors même que son propre détail départemental "
  "contient des poches de 1 an sur 5 à 1 an sur 9.")}</p>
<p class="note">{T(
  "ERA5 (not mapped here, included in the data files) independently puts "
  "much of the same Tahoua–Dosso belt at its driest June–July of the "
  "1981–2026 record — though ERA5 is the weakest of the witnesses against "
  "station data historically and has run anomalously dry over Niger in "
  "2026.",
  "ERA5 (non cartographié ici, inclus dans les fichiers de données) place "
  "indépendamment une grande partie de la même bande Tahoua–Dosso à son "
  "juin–juillet le plus sec de l’historique 1981–2026 — même si ERA5 est "
  "historiquement le moins fiable des témoins face aux données de "
  "stations et s’est montré anormalement sec sur le Niger en 2026.")}</p>
<figure>
<img src="data:image/png;base64,{img_pixel}" alt="CHIRPS pixel percentile map">
<figcaption>{T(
  "Percentile of the 2026 June–July rainfall total within 1981–2025, per "
  "CHIRPS 0.05° pixel. Brown = dry, green = wet; pixels with a June–July "
  "climatology under 40 mm (Saharan north) are masked.",
  "Percentile du cumul juin–juillet 2026 au sein de 1981–2025, par pixel "
  "CHIRPS 0,05°. Brun = sec, vert = humide&nbsp;; les pixels dont la "
  "climatologie juin–juillet est inférieure à 40&nbsp;mm (nord saharien) "
  "sont masqués.")}</figcaption>
</figure>
<figure>
<img src="data:image/png;base64,{img_rain}" alt="Rainfall return period maps">
<figcaption>{T(
  "Return period of the 2026 season per department (rank of 2026 within "
  "the full record, Weibull (n+1)/rank). Left: CHIRPS June–July totals "
  "(46 years). Centre: IMERG 1 June – 30 August totals (29 years). Right: "
  "ENACTS June–July SPI (36 years; grey: no ENACTS coverage in the "
  "Saharan north).",
  "Période de retour de la saison 2026 par département (rang de 2026 dans "
  "l’historique complet, Weibull (n+1)/rang). Gauche&nbsp;: cumuls CHIRPS "
  "juin–juillet (46&nbsp;ans). Centre&nbsp;: cumuls IMERG 1ᵉʳ juin – "
  "30 août (29&nbsp;ans). Droite&nbsp;: SPI juin–juillet ENACTS "
  "(36&nbsp;ans&nbsp;; gris&nbsp;: pas de couverture ENACTS dans le nord "
  "saharien).")}</figcaption>
</figure>

<h2>{T("Observed rainfall — rain gauges",
       "Précipitations observées — pluviomètres")}</h2>
<p>{T(
  "Niger's synoptic gauges (DMN) reach the public domain through the WMO "
  "GTS: monthly CLIMAT reports archived by OGIMET since 2008 (with some "
  "gap months). June + July 2026 station totals are ranked against each "
  "station's own 2008–2026 CLIMAT record. The gauges confirm the eastern "
  "dryness (Maïné-Soroa's July, 33 mm, is under a third of its archive's "
  "median July of ≈ 110 mm) and a broadly normal-to-wet west — including near-normal "
  "totals at Tahoua and Dosso towns, where all three gridded products put "
  "the surrounding departments at severe deficits. Point gauges at towns "
  "and departmental averages can genuinely differ; this heterogeneity is "
  "exactly why localized pockets escape zone-wide indicators.",
  "Les stations synoptiques du Niger (DMN) parviennent au domaine public "
  "via le SMT de l’OMM&nbsp;: messages mensuels CLIMAT archivés par OGIMET "
  "depuis 2008 (avec quelques mois manquants). Les cumuls juin + juillet "
  "2026 par station sont classés dans l’historique CLIMAT 2008–2026 de "
  "chaque station. Les pluviomètres confirment la sécheresse de "
  "l’est (le mois de juillet de Maïné-Soroa, 33&nbsp;mm, est inférieur au "
  "tiers de la médiane de juillet de son archive, ≈ 110&nbsp;mm) et un "
  "ouest globalement normal à "
  "humide — y compris des cumuls proches de la normale aux villes de "
  "Tahoua et de Dosso, alors que les trois produits maillés placent les "
  "départements environnants en déficit sévère. Un pluviomètre ponctuel "
  "en ville et une moyenne départementale peuvent réellement "
  "différer&nbsp;; cette hétérogénéité est précisément la raison pour "
  "laquelle des poches localisées échappent aux indicateurs calculés sur "
  "l’ensemble de la zone.")}</p>
<figure>
<img src="data:image/png;base64,{img_gauge}" alt="Gauge map">
<figcaption>{T(
  "June–July 2026 gauge totals, coloured by return period within each "
  "station's 2008–2026 record.",
  "Cumuls juin–juillet 2026 aux stations, colorés par période de retour au "
  "sein de l’historique 2008–2026 de chaque station.")}</figcaption>
</figure>
<div class="tablewrap">
<table>
<tr>
  <th>{T("Station", "Station")}</th>
  <th>{T("Jun–Jul 2026 (mm)", "Juin–juil. 2026 (mm)")}</th>
  <th>{T("Dry rank", "Rang sec")}</th>
  <th>{T("RP (yrs)", "PR (ans)")}</th>
</tr>
{gauge_rows()}
</table>
</div>
<div class="callout">{T(
  "Diffa's July 2026 CLIMAT report transmitted 447 mm in 4 rain days — "
  "inconsistent with the station's own synoptic reports (≈ 27 mm), with "
  "gauge-calibrated CHIRPS at the town (≈ 88 mm) and with every other "
  "drought signal in the department. It is treated as a transmission error "
  "and excluded, so Diffa shows no 2026 gauge value here.",
  "Le message CLIMAT de Diffa pour juillet 2026 transmet 447&nbsp;mm en "
  "4&nbsp;jours de pluie — incohérent avec les propres messages "
  "synoptiques de la station (≈ 27&nbsp;mm), avec CHIRPS, calé sur les "
  "pluviomètres, à la ville (≈ 88&nbsp;mm) et avec tous les autres "
  "signaux de sécheresse du département. Il est traité comme une erreur "
  "de transmission et exclu&nbsp;; Diffa n’affiche donc pas de valeur "
  "pluviométrique 2026 ici.")}</div>

<h2>{T("Vegetation — FAO ASI and VHI", "Végétation — ASI et VHI de la FAO")}</h2>
<p>{T(
  "The FAO Agricultural Stress Index (ASI) is the share of cropland with a "
  "vegetation health index below 35 during the growing season; VHI combines "
  "NDVI-based vegetation condition with thermal stress. Both are shown for "
  "the latest dekad (11–20 August 2026) against the same dekad in every "
  "year since 1984.",
  "L’indice de stress agricole (ASI) de la FAO est la part des terres "
  "cultivées dont l’indice de santé de la végétation est inférieur à 35 "
  "pendant la campagne&nbsp;; le VHI combine l’état de la végétation dérivé "
  "du NDVI et le stress thermique. Les deux sont montrés pour la dernière "
  "décade (11–20 août 2026) face à la même décade de chaque année depuis "
  "1984.")}</p>
<figure>
<img src="data:image/png;base64,{img_veg}" alt="ASI and VHI strip plots">
<figcaption>{T(
  "Region values for the 11–20 August dekad: grey = 1984–2025, red = 2026. "
  "High ASI is bad (more stressed cropland); low VHI is bad.",
  "Valeurs régionales pour la décade du 11–20 août&nbsp;: gris = "
  "1984–2025, rouge = 2026. Un ASI élevé est défavorable (plus de cultures "
  "stressées)&nbsp;; un VHI bas est défavorable.")}</figcaption>
</figure>
<figure>
<img src="data:image/png;base64,{fao_ndvi}" alt="FAO NDVI anomaly map"
     style="max-width:49%; min-width:320px;">
<img src="data:image/png;base64,{fao_asi}" alt="FAO ASI map"
     style="max-width:49%; min-width:320px;">
<figcaption>{T(
  "FAO GIEWS/ASIS maps for the 11–20 August 2026 dekad. Left: NDVI anomaly "
  "vs the long-term average (brown/red = below normal) — note the deficits "
  "along the southern agricultural belt of Zinder/Maradi and the far "
  "south-east (Diffa). Right: ASI per GAUL-2 area — south-eastern Diffa "
  "shows 25–40% of cropland stressed. Source: FAO GIEWS Earth Observation "
  "(open data).",
  "Cartes FAO GIEWS/ASIS pour la décade du 11–20 août 2026. Gauche&nbsp;: "
  "anomalie de NDVI par rapport à la moyenne de long terme (brun/rouge = "
  "sous la normale) — noter les déficits le long de la bande agricole sud "
  "de Zinder/Maradi et l’extrême sud-est (Diffa). Droite&nbsp;: ASI par "
  "zone GAUL-2 — le sud-est de Diffa montre 25–40&nbsp;% de cultures "
  "stressées. Source&nbsp;: FAO GIEWS Earth Observation (données "
  "ouvertes).")}</figcaption>
</figure>

<h2>{T("End-of-season outlook — SEAS5+ERA5 hybrid, skill-filtered",
       "Perspective de fin de saison — hybride SEAS5+ERA5, filtré selon la performance")}</h2>
<p>{T(
  "Following the team's SEAS5 skill methodology, the outlook is the "
  "combined SEAS5+ERA5 hybrid: for JAS, July comes from ERA5 observations "
  "and August–September from the August-issued ECMWF SEAS5 forecast, each "
  "forecast month bias-corrected against ERA5 before blending. The hybrid "
  "is normalized to the ERA5 distribution and both forecast and "
  "observations are linearly detrended in log space (the skill explorer's "
  "usual Detrended variant), so the 2026 position is measured against the "
  "trend-adjusted climate rather than inflated by the Sahel's recent "
  "wetting trend. Values are only shown where the detrended historical "
  "performance is adequate (Pearson r ≥ 0.30 over 45 hindcast years; "
  "blank otherwise). The JAS hybrid reads as confidence about how the "
  "season ends — its performance is naturally high since July is already "
  "observed. ASO is a pure forecast for the end of the season.",
  "Suivant la méthodologie d’évaluation de SEAS5 de l’équipe, la "
  "perspective est l’hybride combiné SEAS5+ERA5&nbsp;: pour JAS, juillet "
  "provient des observations ERA5 et août–septembre de la prévision SEAS5 "
  "(CEPMMT) émise en août, chaque mois prévu étant corrigé de son biais "
  "par rapport à ERA5 avant combinaison. L’hybride est normalisé sur la "
  "distribution d’ERA5 et prévision comme observations sont détendancées "
  "linéairement en espace log (la variante Détendancée habituelle de "
  "l’explorateur de performance), de sorte que la position de 2026 se "
  "mesure par rapport au climat corrigé de la tendance, plutôt que gonflée "
  "par le récent verdissement du Sahel. Les valeurs ne sont montrées que "
  "là où la performance historique détendancée est suffisante (r de "
  "Pearson ≥ 0,30 sur 45 années de re-prévisions&nbsp;; vide sinon). "
  "L’hybride JAS se lit comme un niveau de confiance sur la fin de "
  "saison — sa performance est naturellement élevée puisque juillet est "
  "déjà observé. ASO est une prévision pure pour la fin de saison.")}</p>
<figure>
<img src="data:image/png;base64,{img_seas5}" alt="SEAS5 return period maps">
<figcaption>{T(
  "Return period of the detrended 2026 hybrid within the detrended "
  "1981–2025 hindcast distribution (dry tail), issued August 2026. Left: "
  "JAS (ERA5 July + SEAS5 August–September). Right: ASO (pure SEAS5 "
  "forecast).",
  "Période de retour de l’hybride 2026 détendancé dans la distribution "
  "des re-prévisions 1981–2025 détendancées (queue sèche), émission d’août "
  "2026. Gauche&nbsp;: JAS (juillet ERA5 + août–septembre SEAS5). "
  "Droite&nbsp;: ASO (prévision SEAS5 pure).")}</figcaption>
</figure>

<h2>{T("Humanitarian needs (2026 HNRP)",
       "Besoins humanitaires (HNRP 2026)")}</h2>
<p>{T(
  "The 2026 Niger HNRP's JIAF intersectoral severity per department "
  "(1 = minimal … 5 = catastrophic; Niger's 2026 analysis assigns up to "
  "class 4). The four class-4 departments — N'Guigmi (Diffa) and Bankilaré, "
  "Téra, Torodi (Tillabéri) — all sit inside 2026 drought pockets: "
  "N'Guigmi has the single driest IMERG June–August on record and Téra / "
  "Bankilaré combine rainfall deficits with the dry JAS outlook.",
  "Sévérité intersectorielle JIAF du HNRP 2026 du Niger par département "
  "(1 = minimale … 5 = catastrophique&nbsp;; l’analyse 2026 du Niger "
  "atteint la classe 4). Les quatre départements en classe 4 — N'Guigmi "
  "(Diffa) et Bankilaré, Téra, Torodi (Tillabéri) — se trouvent tous dans "
  "des poches de sécheresse 2026&nbsp;: N'Guigmi enregistre le juin–août "
  "IMERG le plus sec de l’historique et Téra / Bankilaré combinent déficits "
  "pluviométriques et perspective JAS sèche.")}</p>
<figure>
<img src="data:image/png;base64,{img_hnrp}" alt="HNRP severity map">
<figcaption>{T(
  "2026 HNRP JIAF intersectoral final severity by department. Source: OCHA "
  "HPC / JIAF workbook via the team's HPC mirror.",
  "Sévérité intersectorielle finale JIAF du HNRP 2026 par département. "
  "Source&nbsp;: HPC OCHA / classeur JIAF via le miroir HPC de "
  "l’équipe.")}</figcaption>
</figure>

<h2>{T("Method and sources", "Méthode et sources")}</h2>
<ul class="note">
<li>{T(
  "Return periods: Weibull plotting position — the 2026 value is ranked "
  "within the indicator's full record including 2026 (rank 1 = most "
  "drought-like) and RP = (n+1)/rank. A short record caps the largest "
  "expressible RP (IMERG: 30, gauges: ~20), so identical colours can "
  "understate rarity for short-record indicators.",
  "Périodes de retour&nbsp;: position de tracé de Weibull — la valeur 2026 "
  "est classée dans l’historique complet de l’indicateur, 2026 inclus "
  "(rang 1 = le plus sec), et PR = (n+1)/rang. Un historique court plafonne "
  "la plus grande PR exprimable (IMERG&nbsp;: 30, pluviomètres&nbsp;: "
  "~20)&nbsp;; à couleur identique, la rareté peut donc être sous-estimée "
  "pour les indicateurs à historique court.")}</li>
<li>{T(
  "ENACTS MON June–July SPI per department from the IRI fbfmaproom export "
  "API (DMN gauge + satellite analysis, 1991–2026; the MON series is "
  "revised as the record extends, so values can shift between pulls); "
  "CHIRPS v2.0 Africa monthly (CHC, final through July 2026); IMERG daily "
  "zonal means from the team raster-stats pipeline (through 30 Aug 2026); "
  "ERA5/SEAS5 monthly zonal means from the team database (SEAS5 issued "
  "5 Aug 2026); FAO GIEWS/ASIS dekadal ASI & VHI per region (through "
  "20 Aug 2026); OGIMET CLIMAT gauge archive (2008–2026); HNRP severity "
  "and PiN from the OCHA HPC mirror (2026 plan).",
  "SPI juin–juillet ENACTS MON par département via l’API d’export du "
  "fbfmaproom de l’IRI (analyse pluviomètres + satellite de la DMN, "
  "1991–2026&nbsp;; la série MON est révisée à mesure que l’historique "
  "s’allonge, les valeurs peuvent donc bouger d’une extraction à "
  "l’autre)&nbsp;; CHIRPS v2.0 Afrique mensuel (CHC, final jusqu’à "
  "juillet 2026)&nbsp;; "
  "moyennes zonales journalières IMERG du pipeline raster-stats de "
  "l’équipe (jusqu’au 30 août 2026)&nbsp;; moyennes zonales mensuelles "
  "ERA5/SEAS5 de la base de l’équipe (SEAS5 émis le 5 août 2026)&nbsp;; "
  "ASI et VHI décadaires FAO GIEWS/ASIS par région (jusqu’au 20 août "
  "2026)&nbsp;; archive CLIMAT d’OGIMET pour les pluviomètres "
  "(2008–2026)&nbsp;; sévérité et PiN du HNRP via le miroir HPC de l’OCHA "
  "(plan 2026).")}</li>
<li>{T(
  "This is a monitoring analysis, not the AA framework trigger: the "
  "framework's own observational indicator (ENACTS June–July SPI over the "
  "monitored zone) read −0.12 in 2026 — no trigger — while several of the "
  "sub-national indicators here are far drier. Zone-wide averages dilute "
  "localized droughts; that is exactly what this page is meant to surface.",
  "Ceci est une analyse de suivi, pas le déclencheur du cadre d’action "
  "anticipatoire&nbsp;: l’indicateur observationnel propre au cadre (SPI "
  "juin–juillet ENACTS sur la zone suivie) valait −0,12 en 2026 — seuil "
  "non atteint — alors que plusieurs indicateurs infranationaux présentés "
  "ici sont bien plus secs. Les moyennes zonales diluent les sécheresses "
  "localisées&nbsp;; c’est précisément ce que cette page vise à faire "
  "apparaître.")}</li>
</ul>

<footer>
{T("Generated from <code>exploration/pockets_page.py</code> · "
   "OCHA Centre for Humanitarian Data · data sources as cited above.",
   "Généré par <code>exploration/pockets_page.py</code> · Centre de "
   "données humanitaires de l’OCHA · sources citées ci-dessus.")}
</footer>
</main>
<script>
window.AA_TITLES = {{
  en: "Niger 2026 — pockets of drought",
  fr: "Niger 2026 — poches de sécheresse"
}};
function aaSetLang(l) {{
  document.documentElement.setAttribute("data-lang", l);
  document.documentElement.setAttribute("lang", l);
  try {{ localStorage.setItem("aa-lang", l); }} catch (e) {{}}
  document.title = window.AA_TITLES[l] || document.title;
  document.getElementById("btn-en").classList.toggle("active", l === "en");
  document.getElementById("btn-fr").classList.toggle("active", l === "fr");
  document.dispatchEvent(new CustomEvent("aalang", {{detail: l}}));
}}
document.addEventListener("DOMContentLoaded", function () {{
  var l = "en";
  try {{ l = localStorage.getItem("aa-lang") || "en"; }} catch (e) {{}}
  aaSetLang(l);
}});
</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
