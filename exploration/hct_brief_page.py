"""Render the 6-slide HCT briefing deck (El Niño & the 2026 season).

A static, bilingual (EN/FR toggle) HTML slide deck at
``docs/hct-brief/index.html``: arrow keys / buttons to navigate, print to
PDF for distribution (one slide per landscape page). Figures are reused
from the pockets analysis (``pockets_figures``) and from the team's
published Niger ENSO slides in the sibling ``ds-seas5-skill`` clone
(``pages/enso/slides/NER_slide{1,2}[_fr].svg``, refreshed with the
September 2026 issuance).

Usage: ``uv run python exploration/hct_brief_page.py``
"""

import base64
from pathlib import Path

import pandas as pd
import pockets_figures as figs

D = Path(__file__).parent / "public" / "pockets"
OUT = Path(__file__).parent.parent / "docs" / "hct-brief" / "index.html"
ENSO_DIR = (
    Path(__file__).resolve().parents[2]
    / "ds-seas5-skill"
    / "pages"
    / "enso"
    / "slides"
)


def T(en, fr):
    return (
        f'<span class="lv lv-en">{en}</span>'
        f'<span class="lv lv-fr">{fr}</span>'
    )


def svg_uri(path):
    b = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/svg+xml;base64,{b}"


def img_dual(en_src, fr_src, alt):
    return (
        f'<img class="lv lv-en" src="{en_src}" alt="{alt}">'
        f'<img class="lv lv-fr" src="{fr_src}" alt="{alt}">'
    )


def main():
    summary = pd.read_csv(D / "summary_adm2.csv")
    comp = pd.read_csv(D / "composite_adm2.csv")

    print("rendering figures…", flush=True)
    img_cdi = figs.fig_cdi(summary)
    img_asap = figs.fig_asap()
    img_strip = figs.fig_cdi_history(
        comp,
        [1997, 2006, 2009, 2011, 2021, 2026],
        cerf_years={2009, 2011, 2021},
        ncols=3,
        panel_w=4.4,
        panel_h=2.15,
        extent=((-0.3, 16.2), (11.3, 17.8)),
        subtitles={
            1997: "mauvaise année / bad year (pré-CERF)",
            2006: "fausse alerte / false alarm",
            2009: "CERF ~$35M (2010)",
            2011: "CERF ~$22M (2011–12)",
            2021: "CERF $10M · manqué / missed",
            2026: "aujourd'hui / today",
        },
    )
    img_ch = figs.fig_ch_lean()
    img_bars = figs.fig_indicator_bars(
        comp, cerf_years={2008, 2009, 2011, 2021}, aa_years={2022}
    )
    enso1_en = svg_uri(ENSO_DIR / "NER_slide1.svg")
    enso1_fr = svg_uri(ENSO_DIR / "NER_slide1_fr.svg")
    enso2_en = svg_uri(ENSO_DIR / "NER_slide2.svg")
    enso2_fr = svg_uri(ENSO_DIR / "NER_slide2_fr.svg")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Niger 2026 — HCT briefing</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a; background: #444; margin: 0;
  }}
  .slide {{
    background: #ffffff; width: 1280px; max-width: 96vw;
    aspect-ratio: 16 / 9; margin: 1.2rem auto; padding: 2.2rem 2.8rem;
    box-shadow: 0 2px 14px rgba(0,0,0,0.35);
    display: flex; flex-direction: column; overflow: hidden;
    position: relative;
  }}
  .slide h1 {{ font-size: 2.1rem; margin: 0 0 0.4rem; color: #0b3d6b; }}
  .slide h2 {{ font-size: 1.55rem; margin: 0 0 0.8rem; color: #0b3d6b;
              border-bottom: 3px solid #2a6fb0; padding-bottom: 0.35rem; }}
  .slide ul {{ font-size: 1.08rem; line-height: 1.5; margin: 0.4rem 0;
              padding-left: 1.3rem; }}
  .slide li {{ margin-bottom: 0.55rem; }}
  .cols {{ display: flex; gap: 1.6rem; flex: 1; min-height: 0;
          align-items: stretch; }}
  .cols .fig {{ flex: 1.35; display: flex; align-items: center;
               justify-content: center; min-width: 0; }}
  .cols .txt {{ flex: 1; min-width: 0; }}
  .fig img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
  .fullfig {{ flex: 1; display: flex; align-items: center;
             justify-content: center; min-height: 0; }}
  .fullfig img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
  .keybox {{ background: #f2f7fb; border-left: 5px solid #2a6fb0;
            padding: 0.7rem 1.1rem; margin-top: 1rem; font-size: 1.15rem; }}
  .keybox li {{ margin-bottom: 0.7rem; }}
  .foot {{ position: absolute; bottom: 0.7rem; left: 2.8rem; right: 2.8rem;
          display: flex; justify-content: space-between;
          color: #888; font-size: 0.78rem; }}
  .note {{ color: #555; font-size: 0.9rem; font-style: italic; }}
  .titlemeta {{ color: #555; font-size: 1.1rem; margin-bottom: 0.4rem; }}
  .navbar {{ position: fixed; top: 0.6rem; right: 0.9rem; z-index: 10; }}
  .navbar button, .navbar a {{
    border: 1px solid #ccc; background: #fff; padding: 4px 12px;
    cursor: pointer; font-size: 0.85rem; text-decoration: none;
    color: #1a1a1a; }}
  .navbar button.active {{ background: #2a6fb0; color: #fff;
    border-color: #2a6fb0; }}
  .lv {{ display: none; }}
  html[data-lang="en"] .lv-en {{ display: inline; }}
  html[data-lang="fr"] .lv-fr {{ display: inline; }}
  html:not([data-lang]) .lv-en {{ display: inline; }}
  html[data-lang="en"] img.lv-en, html:not([data-lang]) img.lv-en
    {{ display: block; }}
  html[data-lang="fr"] img.lv-fr {{ display: block; }}
  @media print {{
    body {{ background: #fff; }}
    .navbar {{ display: none; }}
    .slide {{ box-shadow: none; margin: 0; width: 100%; max-width: none;
             page-break-after: always; }}
    @page {{ size: 297mm 167mm; margin: 0; }}
  }}
</style>
</head>
<body>
<div class="navbar">
  <button id="btn-en" onclick="aaSetLang('en')">EN</button>
  <button id="btn-fr" onclick="aaSetLang('fr')">FR</button>
  <a href="../">{T("home", "accueil")}</a>
  <a href="#" onclick="window.print();return false;">PDF</a>
</div>

<!-- Slide 1 — title & bottom line -->
<section class="slide">
<h1>{T("Niger's 2026 rainy season — and El Niño",
       "La saison des pluies 2026 au Niger — et El Niño")}</h1>
<p class="titlemeta">{T(
  "Briefing for the Humanitarian Country Team · 9 September 2026 · "
  "OCHA Centre for Humanitarian Data",
  "Briefing pour l'Équipe humanitaire pays · 9 septembre 2026 · "
  "Centre de données humanitaires de l'OCHA")}</p>
<div class="keybox">
<b>{T("Bottom line", "L'essentiel")}</b>
<ul>
<li>{T(
  "A strong El Niño is underway (Niño3.4 ≈ +1.9 °C in August) — but its "
  "direct fingerprint on Niger's rains is weak and patchy: on its own, "
  "El Niño is not much of a driver here, and not a basis for alarm.",
  "Un fort épisode El Niño est en cours (Niño3.4 ≈ +1,9 °C en août) — "
  "mais son empreinte directe sur les pluies du Niger est faible et "
  "hétérogène&nbsp;: à lui seul, El Niño n'est pas un grand facteur "
  "ici, ni un motif d'alarme.")}</li>
<li>{T(
  "What is concerning is specific and current: this season's "
  "observations for Niger — four independent rainfall datasets and the "
  "DMN's own gauges put six departments at a ≥ 1-in-10-year deficit — "
  "and the current seasonal forecasts, which account for El Niño "
  "together with every other driver, point the same way for the rest of "
  "the season.",
  "Ce qui préoccupe est spécifique et actuel&nbsp;: les observations de "
  "cette saison pour le Niger — quatre jeux de données pluviométriques "
  "indépendants et les propres pluviomètres de la DMN placent six "
  "départements en déficit ≥ 1 an sur 10 — et les prévisions "
  "saisonnières actuelles, qui intègrent El Niño avec tous les autres "
  "facteurs, pointent dans le même sens pour la fin de saison.")}</li>
<li>{T(
  "By the same yardstick, 2026's rainfall extent equals early-September "
  "2009 — the season behind Niger's largest CERF drought response. "
  "Unlike 2009, vegetation has not (yet) followed: impacts are only "
  "starting to surface, in the east.",
  "À la même aune, l'étendue pluviométrique de 2026 égale celle de "
  "début septembre 2009 — la saison à l'origine de la plus grande "
  "réponse sécheresse du CERF au Niger. Contrairement à 2009, la "
  "végétation n'a pas (encore) suivi&nbsp;: les impacts ne font "
  "qu'émerger, à l'est.")}</li>
</ul>
</div>
<div class="foot"><span>1 / 7</span>
<span>ocha-dap.github.io/ds-aa-ner-drought/pockets/</span></div>
</section>

<!-- Slide 2 — El Niño teleconnection -->
<section class="slide">
<h2>{T("What El Niño does — and doesn't — tell us about Niger",
       "Ce qu'El Niño dit — et ne dit pas — du Niger")}</h2>
<div class="fullfig">
{img_dual(enso1_en, enso1_fr, "ENSO teleconnection map for Niger")}
</div>
<ul style="font-size:1.0rem">
<li>{T(
  "Isolating El Niño's unique signal (1981–2025, other ocean modes held "
  "constant): weak and patchy over Niger — a moderate dry tendency in "
  "parts of the south-centre and east late in the season, a slight wet "
  "tendency in the west mid-season. Nothing that predicts a national "
  "drought from the El Niño label alone.",
  "En isolant le signal propre d'El Niño (1981–2025, autres modes "
  "océaniques tenus constants)&nbsp;: faible et hétérogène sur le "
  "Niger — tendance sèche modérée sur une partie du centre-sud et de "
  "l'est en fin de saison, légère tendance humide à l'ouest en "
  "mi-saison. Rien qui permette de prédire une sécheresse nationale à "
  "partir du seul label El Niño.")}</li>
<li>{T(
  "The practical consequence: judge the season from seasonal forecasts "
  "(which already account for ENSO and every other driver) and, above "
  "all, from observations — both follow.",
  "Conséquence pratique&nbsp;: juger la saison sur les prévisions "
  "saisonnières (qui intègrent déjà l'ENSO et tous les autres facteurs) "
  "et, surtout, sur les observations — les deux suivent.")}</li>
</ul>
<div class="foot"><span>2 / 7</span><span>ERA5 × Niño3.4 (NOAA PSL),
partial correlation · OCHA CHD teleconnections</span></div>
</section>

<!-- Slide 3 — observations -->
<section class="slide">
<h2>{T("What has already been observed", "Ce qui est déjà observé")}</h2>
<div class="cols">
<div class="fig"><img src="data:image/png;base64,{img_cdi}"
  alt="Combined drought indicator map"></div>
<div class="txt">
<ul style="font-size:0.98rem">
<li>{T(
  "Four independent rainfall datasets (CHIRPS, IMERG, the DMN's ENACTS, "
  "SEAS5+ERA5) are combined per department; classes require majority "
  "agreement.",
  "Quatre jeux de données pluviométriques indépendants (CHIRPS, IMERG, "
  "l'ENACTS de la DMN, SEAS5+ERA5) sont combinés par département&nbsp;; "
  "les classes exigent un accord majoritaire.")}</li>
<li>{T(
  "Severe rainfall deficit (≥ 1-in-10-year, orange): Keita (Tahoua), "
  "Dioundiou, Dosso, Gaya, Loga (Dosso), Tanout (Zinder). 18 more "
  "departments on watch, including eastern Diffa and the Tahoua belt.",
  "Déficit pluviométrique sévère (≥ 1 an sur 10, orange)&nbsp;: Keita "
  "(Tahoua), Dioundiou, Dosso, Gaya, Loga (Dosso), Tanout (Zinder). 18 "
  "autres départements en vigilance, dont l'est de Diffa et la bande de "
  "Tahoua.")}</li>
<li>{T(
  "The national met service's own gauges concur in the east: four "
  "stations coded August in their driest quintile against DMN's 30-year "
  "normals; five recorded their 2nd-driest June–August on record.",
  "Les pluviomètres du service météorologique national concordent à "
  "l'est&nbsp;: quatre stations codent août dans leur quintile le plus "
  "sec par rapport aux normales trentenaires de la DMN&nbsp;; cinq "
  "enregistrent leur 2ᵉ juin–août le plus sec.")}</li>
<li>{T(
  "Hatched: the four HNRP severity-4 departments. On the combined "
  "(majority) indicator only N'Guigmi reaches watch — but each of the "
  "four is in deficit in at least one dataset: IMERG has N'Guigmi at "
  "its driest June–August on record, and Téra, Bankilaré and Torodi at "
  "1-in-7 to 1-in-15, while the gauge-anchored datasets read them "
  "closer to normal.",
  "Hachures&nbsp;: les quatre départements en sévérité 4 du HNRP. Sur "
  "l'indicateur combiné (majoritaire), seul N'Guigmi atteint la "
  "vigilance — mais chacun des quatre est en déficit dans au moins un "
  "jeu de données&nbsp;: IMERG place N'Guigmi à son juin–août le plus "
  "sec de l'historique, et Téra, Bankilaré et Torodi entre 1 an sur 7 "
  "et 1 an sur 15, tandis que les jeux ancrés sur les pluviomètres les "
  "lisent plus proches de la normale.")}</li>
</ul>
</div>
</div>
<div class="foot"><span>3 / 7</span><span>CHIRPS · IMERG · ENACTS ·
SEAS5+ERA5 · FAO ASIS · OGIMET/DMN · HNRP 2026</span></div>
</section>

<!-- Slide 4 — agricultural impact (JRC ASAP) -->
<section class="slide">
<h2>{T("ASAP warnings", "Alertes ASAP")}</h2>
<div class="fullfig">
<img src="data:image/png;base64,{img_asap}" alt="JRC ASAP warnings map">
</div>
<ul style="font-size:1.0rem">
<li>{T(
  "The EC/JRC ASAP system issues automated agricultural-drought warnings "
  "per unit and land cover every 10 days. Current picture: warnings on "
  "29 of 35 units (cropland and/or rangeland) — the Dosso–Tahoua–"
  "Tillabéri belt at level 1/1+, "
  "and level-3 warnings — poor growth "
  "with negative prospects, from water balance AND biomass — on Diffa, "
  "Maïné-Soroa and Tanout croplands, level 3+ on N'Guigmi rangelands.",
  "Le système ASAP de la CE/JRC émet tous les 10 jours des alertes "
  "automatiques de sécheresse agricole par unité et type de couvert. "
  "Tableau actuel&nbsp;: alertes sur 29 des 35 unités (cultures et/ou "
  "pâturages) — la bande Dosso–Tahoua–Tillabéri en niveau 1/1+, et des "
  "alertes de niveau 3 — "
  "croissance médiocre et perspectives négatives, sur bilan hydrique ET "
  "biomasse — sur les cultures de Diffa, Maïné-Soroa et Tanout, niveau "
  "3+ sur les pâturages de N'Guigmi.")}</li>
<li>{T(
  "Region-scale vegetation indices (FAO ASI/VHI) are not yet "
  "exceptional — impacts typically lag the rainfall deficit, and the "
  "east is where they are surfacing first. September dekads are the "
  "watchpoint.",
  "Les indices de végétation à l'échelle régionale (ASI/VHI de la FAO) "
  "ne sont pas encore exceptionnels — les impacts suivent généralement "
  "le déficit de pluie, et c'est à l'est qu'ils émergent en premier. "
  "Les décades de septembre sont le point de vigilance.")}</li>
</ul>
<div class="foot"><span>4 / 7</span><span>EC/JRC ASAP,
agricultural-production-hotspots.ec.europa.eu · {T("dekad", "décade")}
21–31/08/2026</span></div>
</section>

<!-- Slide 5 — forecast -->
<section class="slide">
<h2>{T("The rest of the season, per the forecasts",
       "La fin de saison, selon les prévisions")}</h2>
<div class="fullfig">
{img_dual(enso2_en, enso2_fr, "SEAS5 September issuance for Niger")}
</div>
<ul style="font-size:1.0rem">
<li>{T(
  "With July–August observed, the season-closing JAS estimate is the "
  "driest of the 46-year record (per the ERA5-based system, which runs "
  "anomalously dry this year — the direction is corroborated by the "
  "other datasets, the extremity less so).",
  "Juillet–août observés, l'estimation de clôture JAS est la plus sèche "
  "de l'historique de 46 ans (selon le système fondé sur ERA5, "
  "anormalement sec cette année — la direction est corroborée par les "
  "autres jeux de données, l'extrémité moins).")}</li>
<li>{T(
  "The remaining true forecast — September–November, the harvest and "
  "pasture-regrowth window — tilts dry: ~1-in-4 nationally, up to "
  "1-in-10 in Dosso/Tillabéri pockets.",
  "La véritable prévision restante — septembre–novembre, fenêtre des "
  "récoltes et de la repousse des pâturages — penche au sec&nbsp;: "
  "~1 an sur 4 au niveau national, jusqu'à 1 an sur 10 dans des poches "
  "de Dosso/Tillabéri.")}</li>
</ul>
<div class="foot"><span>5 / 7</span><span>ECMWF SEAS5, {T("issued",
"émission")} 09/2026 · OCHA CHD skill methodology</span></div>
</section>

<!-- Slide 6 — comparison & implications -->
<section class="slide">
<h2>{T("How 2026 compares — and what it means",
       "2026 en comparaison — et ce que cela implique")}</h2>
<div class="fullfig" style="flex:0.9">
<img src="data:image/png;base64,{img_strip}"
  alt="1997, 2006, 2009, 2011, 2021 and 2026 compared">
</div>
<ul style="font-size:0.98rem">
<li>{T(
  "The indicator flagged the CERF drought seasons at this same point of "
  "the year — 2009 (24 units, ≈US$35M of CERF responses) and 2011 (20 "
  "units, ≈$22M) — and it also catches 1997, the 8th-worst season in "
  "the framework's own impact record, before CERF existed. 2026 "
  "matches 2009's extent.",
  "L'indicateur signalait les saisons de sécheresse CERF au même "
  "moment de l'année — 2009 (24 unités, ≈35 M$ de réponses CERF) et "
  "2011 (20 unités, ≈22 M$) — et il capte aussi 1997, 8ᵉ pire saison "
  "du propre registre d'impact du cadre, avant l'existence du CERF. "
  "2026 égale l'étendue de 2009.")}</li>
<li>{T(
  "It can also over-call: 2006 was loud (23 units) yet no bad year "
  "followed — rainfall alone can false-alarm, which is why vegetation "
  "(ASAP) and food-security confirmation matter. And 2021 shows the "
  "blind spot — its rains collapsed in September itself. A quiet "
  "early-September map is not an all-clear; a loud one, as now, is "
  "meaningful but not yet a verdict.",
  "Il peut aussi trop alerter&nbsp;: 2006 était chargé (23 unités) "
  "sans mauvaise année à la clé — la pluie seule peut produire une "
  "fausse alerte, d'où l'importance de la confirmation par la "
  "végétation (ASAP) et la sécurité alimentaire. Et 2021 montre "
  "l'angle mort — ses pluies se sont effondrées en septembre même. Une "
  "carte calme début septembre n'est pas un feu vert&nbsp;; une carte "
  "chargée, comme aujourd'hui, est significative mais pas encore un "
  "verdict.")}</li>
</ul>
<div class="foot"><span>6 / 7</span>
<span>{T("framework bad-year record · aa.cerf_allocation",
"registre des mauvaises années du cadre · aa.cerf_allocation")}</span></div>
</section>

<!-- Slide 7 — 35 seasons in one chart & next steps -->
<section class="slide">
<h2>{T("35 seasons in one chart — and what to do now",
       "35 saisons en un graphique — et la suite")}</h2>
<div class="fullfig" style="flex:1.05">
<img src="data:image/png;base64,{img_bars}"
  alt="Departments in rainfall deficit and vegetation stress per year">
</div>
<ul style="font-size:0.98rem">
<li>{T(
  "Top: departments in rainfall deficit (RP ≥ 5; dark: ≥ 10). Bottom: "
  "departments whose region shows vegetation stress. Red bands: CERF "
  "drought seasons. 2026's rainfall count is the largest since "
  "2009–2011 — its vegetation count is still low, which is the key "
  "September uncertainty.",
  "Haut&nbsp;: départements en déficit pluviométrique (PR ≥ 5&nbsp;; "
  "foncé&nbsp;: ≥ 10). Bas&nbsp;: départements dont la région montre un "
  "stress de la végétation. Bandes rouges&nbsp;: saisons de sécheresse "
  "CERF. Le décompte pluviométrique de 2026 est le plus élevé depuis "
  "2009–2011 — celui de la végétation reste bas, la grande incertitude "
  "de septembre.")}</li>
<li>{T(
  "Next steps: follow the hotspot departments (live page below); watch "
  "September rainfall and vegetation dekads and the November Cadre "
  "Harmonisé analysis; factor a 2009-type lean season into planning and "
  "prepositioning, especially where deficits overlap HNRP severity-4 "
  "areas (eastern Diffa, western Tillabéri).",
  "Suites proposées&nbsp;: suivre les départements sensibles (page en "
  "direct ci-dessous)&nbsp;; surveiller les pluies et décades de "
  "végétation de septembre et l'analyse du Cadre harmonisé de "
  "novembre&nbsp;; intégrer une soudure de type 2009 dans la "
  "planification et le prépositionnement, en particulier là où les "
  "déficits recoupent les zones en sévérité 4 du HNRP (est de Diffa, "
  "ouest de Tillabéri).")}</li>
</ul>
<div class="foot"><span>7 / 7</span>
<span>ocha-dap.github.io/ds-aa-ner-drought/pockets/</span></div>
</section>

<!-- Backup slide — Cadre Harmonisé -->
<section class="slide">
<h2>{T("Backup — food security after past seasons (Cadre Harmonisé)",
       "Annexe — la sécurité alimentaire après les saisons passées (Cadre harmonisé)")}</h2>
<div class="fullfig" style="flex:1.05">
<img src="data:image/png;base64,{img_ch}"
  alt="Cadre Harmonise June-August phase 3+ by year">
</div>
<ul style="font-size:0.98rem">
<li>{T(
  "June–August lean-season population in CH phase 3+ (projected each "
  "spring). After the 2021 drought season, the 2022 lean season reached "
  "4.4 million in phase 3+ — including 426,000 in phase 4, both records "
  "of the CH era and roughly double the pre-drought year.",
  "Population en phase 3+ du CH pendant la soudure juin–août (projetée "
  "chaque printemps). Après la saison de sécheresse 2021, la soudure "
  "2022 a atteint 4,4 millions en phase 3+ — dont 426 000 en phase 4, "
  "deux records de l'ère CH et environ le double de l'année "
  "précédente.")}</li>
<li>{T(
  "Read with care: CH outcomes reflect conflict, prices, access and "
  "assistance as much as rainfall — they map imperfectly onto drought "
  "indicators (2022 followed the 2021 drought, but 2023–24 stayed high "
  "amid the regional political and economic crisis). The 2026 bar "
  "(hatched) was projected before this season; the November 2026 CH "
  "analysis is the first number that will price in this season's "
  "outcome.",
  "À lire avec prudence&nbsp;: les résultats du CH reflètent le "
  "conflit, les prix, l'accès et l'assistance autant que la pluie — ils "
  "se superposent imparfaitement aux indicateurs de sécheresse (2022 "
  "suit la sécheresse 2021, mais 2023–24 restent élevés dans le "
  "contexte de la crise politique et économique régionale). La barre "
  "2026 (hachurée) a été projetée avant cette saison&nbsp;; l'analyse "
  "CH de novembre 2026 sera le premier chiffre à intégrer l'issue de "
  "cette saison.")}</li>
</ul>
<div class="foot"><span>{T("backup", "annexe")}</span>
<span>Cadre harmonisé (CILSS/HDX)</span></div>
</section>

<script>
window.AA_TITLES = {{
  en: "Niger 2026 — HCT briefing",
  fr: "Niger 2026 — briefing EHP"
}};
function aaSetLang(l) {{
  document.documentElement.setAttribute("data-lang", l);
  document.documentElement.setAttribute("lang", l);
  try {{ localStorage.setItem("aa-lang", l); }} catch (e) {{}}
  document.title = window.AA_TITLES[l] || document.title;
  document.getElementById("btn-en").classList.toggle("active", l === "en");
  document.getElementById("btn-fr").classList.toggle("active", l === "fr");
}}
document.addEventListener("DOMContentLoaded", function () {{
  var l = "en";
  try {{ l = localStorage.getItem("aa-lang") || "en"; }} catch (e) {{}}
  aaSetLang(l);
}});
document.addEventListener("keydown", function (e) {{
  var slides = document.querySelectorAll(".slide");
  var y = window.scrollY, idx = 0;
  slides.forEach(function (s, i) {{
    if (s.offsetTop - 80 <= y) idx = i;
  }});
  if (e.key === "ArrowRight" || e.key === "PageDown") {{
    if (idx < slides.length - 1) slides[idx + 1].scrollIntoView();
  }} else if (e.key === "ArrowLeft" || e.key === "PageUp") {{
    if (idx > 0) slides[idx - 1].scrollIntoView();
  }}
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
