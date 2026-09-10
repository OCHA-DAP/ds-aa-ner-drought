"""Render the ENACTS observational-trigger investigation page.

Static write-up of the 2026 observational decision: the live IRI Maproom
ENACTS MON value vs the CHIRPS/ERA5 proxies, the DMN gauge record (monthly
CLIMAT reports), the historical dataset-vs-gauge benchmark, and the design
implications. All numbers are baked in; sources and methods are documented on
the page itself. Data provenance:

- Maproom values: fbfmaproom2/niger/export API (queried 2026-08-28 and
  2026-09-01)
- CHIRP/CHIRPS/ARC2 series: IRI Data Library, 0-16E / 11-17N
- zone-masked CHIRPS/ERA5: exploration/public/junjul_rainfall.csv
- gauges: DMN monthly CLIMAT via OGIMET (exploration/pockets_fetch_gauges.py
  cache), 2008-2026

Usage: ``python exploration/enacts_page.py`` -> writes docs/enacts/index.html
"""

from pathlib import Path

OUT = Path(__file__).parent.parent / "docs" / "enacts" / "index.html"

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Investigation of the 2026 Niger drought observational trigger: the live IRI Maproom ENACTS value, the CHIRPS/ERA5 disagreement, the DMN gauge record, and design implications.">
<link rel="icon" href="../favicon.ico">
<title>ENACTS and the 2026 Trigger</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root{
    color-scheme: light;
    --paper:#f7f7f5;
    --surface:#fcfcfb;
    --ink:#1c1c1a;
    --ink-2:#52514e;
    --muted:#898781;
    --grid:#e1e0d9;
    --axis:#c3c2b7;
    --border:rgba(11,11,11,.10);
    --accent:#1c5cab;
    --accent-soft:#e7eef8;
    --s1:#2a78d6;   /* series 1: reference / official */
    --s2:#eb6834;   /* series 2: 2026 */
    --warnbg:#fdf6ec;
    --warnbar:#b98718;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      color-scheme: dark;
      --paper:#111110;
      --surface:#1a1a19;
      --ink:#f2f1ec;
      --ink-2:#c3c2b7;
      --muted:#898781;
      --grid:#2c2c2a;
      --axis:#383835;
      --border:rgba(255,255,255,.10);
      --accent:#6da7ec;
      --accent-soft:#182636;
      --s1:#3987e5;
      --s2:#d95926;
      --warnbg:#26200f;
      --warnbar:#d9a83a;
    }
  }
  :root[data-theme="dark"]{
    color-scheme: dark;
    --paper:#111110;
    --surface:#1a1a19;
    --ink:#f2f1ec;
    --ink-2:#c3c2b7;
    --muted:#898781;
    --grid:#2c2c2a;
    --axis:#383835;
    --border:rgba(255,255,255,.10);
    --accent:#6da7ec;
    --accent-soft:#182636;
    --s1:#3987e5;
    --s2:#d95926;
    --warnbg:#26200f;
    --warnbar:#d9a83a;
  }
  body{
    background:var(--paper);
    color:var(--ink);
    font-family:"Source Serif 4", Georgia, serif;
    font-size:16.5px;
    line-height:1.62;
    margin:0;
  }
  .wrap{max-width:960px;margin:0 auto;padding:48px 24px 96px;}
  .prose{max-width:70ch;}
  header.prose{margin-bottom:8px;}
  .eyebrow{
    font-family:"IBM Plex Mono", ui-monospace, monospace;
    font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
    color:var(--accent);font-weight:500;margin:0 0 10px;
  }
  h1{
    font-family:"Archivo", system-ui, sans-serif;
    font-weight:700;font-size:clamp(28px,4.5vw,40px);line-height:1.12;
    text-wrap:balance;margin:0 0 10px;letter-spacing:-.01em;
  }
  .standfirst{font-size:18.5px;color:var(--ink-2);font-style:italic;margin:0 0 6px;}
  .meta{
    font-family:"IBM Plex Mono", ui-monospace, monospace;
    font-size:12px;color:var(--muted);margin:14px 0 0;
  }
  h2{
    font-family:"Archivo", system-ui, sans-serif;
    font-weight:650;font-size:22px;line-height:1.25;text-wrap:balance;
    margin:52px 0 12px;letter-spacing:-.005em;
  }
  h2 .sec{
    font-family:"IBM Plex Mono", ui-monospace, monospace;
    font-size:12px;color:var(--muted);font-weight:400;letter-spacing:.1em;
    display:block;margin-bottom:6px;
  }
  p{margin:0 0 16px;}
  a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:2px;}
  a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px;}
  strong{font-weight:600;}
  .tldr{
    background:var(--surface);
    border:1px solid var(--border);
    border-left:4px solid var(--accent);
    border-radius:6px;
    padding:22px 26px 10px;
    margin:34px 0 8px;
  }
  .tldr h2{margin:0 0 12px;font-size:16px;}
  .tldr p{font-size:15.5px;}
  .callout{
    background:var(--warnbg);
    border:1px solid var(--border);
    border-left:4px solid var(--warnbar);
    border-radius:6px;
    padding:16px 22px;
    margin:22px 0;
    font-size:15px;
  }
  figure{margin:30px 0 8px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:22px 22px 14px;}
  figure .ftitle{
    font-family:"Archivo", system-ui, sans-serif;font-weight:600;font-size:15.5px;margin:0 0 2px;
  }
  figure .fsub{font-family:"IBM Plex Mono", ui-monospace, monospace;font-size:11.5px;color:var(--muted);margin:0 0 14px;}
  figure .chartbox{overflow-x:auto;}
  figcaption{font-size:13.5px;color:var(--ink-2);line-height:1.5;margin-top:12px;max-width:70ch;}
  .legend{display:flex;gap:18px;flex-wrap:wrap;margin:0 0 10px;font-family:"IBM Plex Mono", ui-monospace, monospace;font-size:12px;color:var(--ink-2);}
  .legend .key{display:flex;align-items:center;gap:7px;}
  .swatch{width:10px;height:10px;border-radius:50%;display:inline-block;}
  svg text{font-family:"IBM Plex Mono", ui-monospace, monospace;}
  table{
    border-collapse:collapse;width:100%;margin:20px 0;
    font-family:"IBM Plex Mono", ui-monospace, monospace;font-size:13px;
    font-variant-numeric:tabular-nums;
  }
  th{
    font-family:"Archivo", system-ui, sans-serif;font-size:12.5px;font-weight:600;
    text-align:left;color:var(--ink-2);border-bottom:2px solid var(--axis);
    padding:8px 12px 6px;
  }
  td{border-bottom:1px solid var(--grid);padding:7px 12px;}
  td.num, th.num{text-align:right;}
  .tablewrap{overflow-x:auto;}
  .hit{color:var(--s2);font-weight:500;}
  .tooltip{
    position:fixed;pointer-events:none;z-index:10;
    background:var(--ink);color:var(--paper);
    font-family:"IBM Plex Mono", ui-monospace, monospace;font-size:12px;line-height:1.45;
    padding:8px 11px;border-radius:5px;max-width:260px;
    opacity:0;transition:opacity .12s;
  }
  @media (prefers-reduced-motion: reduce){ .tooltip{transition:none;} }
  ol.talk{padding-left:1.3em;}
  ol.talk li{margin-bottom:14px;}
  ul.qs{padding-left:1.2em;}
  ul.qs li{margin-bottom:10px;}
  .small{font-size:13.5px;color:var(--ink-2);}
  code{font-family:"IBM Plex Mono", ui-monospace, monospace;font-size:.85em;background:var(--accent-soft);padding:1px 5px;border-radius:4px;}
</style>
<style>
  body { padding: 0; }
</style>
</head>
<body>
<!-- back to the site landing page - first element inside body -->
<style>
  .home-link { display:inline-block; margin:14px 0 0 18px; padding:6px 12px;
    font:500 13px/1 Roboto,system-ui,sans-serif; color:#1e795f;
    background:#e9f5f1; border:1px solid #d4eae4; border-radius:4px;
    text-decoration:none; }
  .home-link:hover { background:#d4eae4; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) .home-link { color:#8fd0bc; background:#15221e; border-color:#24463c; }
  }
</style>
<a class="home-link" href="../">&#8592; Niger drought AA</a>



<div class="wrap">
<header class="prose">
  <p class="eyebrow">Niger drought AA · observational arm · briefing</p>
  <h1>Why ENACTS didn’t trigger — and what the gauges actually say</h1>
  <p class="standfirst">The official Jun–Jul SPI came in near normal while our CHIRPS and ERA5 proxies sat at or past the activation threshold. Both readings are real; they disagree about geography, not arithmetic.</p>
  <p class="meta">ds-aa-ner-drought · data pulled live from the IRI Maproom, CHC, IRI Data Library &amp; GTS synop archives · 28 Aug 2026</p>
</header>

<div class="tldr prose">
  <h2>The short version</h2>
  <p><strong>The official value is not marginal.</strong> The live Maproom’s ENACTS MON Jun–Jul SPI for 2026 is <strong>−0.120</strong> — 16th driest of 36 years (≈44th percentile). The 15% threshold sits at −0.712; even the endorsed 35% threshold is −0.362. No plausible rounding gets 2026 across either line.</p>
  <p><strong>The gauges describe pockets, not a zone-wide drought</strong> <em>(revised 1 Sep — the monthly CLIMAT record supersedes the daily-synop reconstruction in the first version of this note)</em>. DMN’s own monthly CLIMAT reports put most stations’ Jun–Jul totals at normal to above normal — the west (Tillabéry, Niamey, Dosso) clearly wet — while the dryness is concentrated in particular months and places: July at Magaria (2nd driest of 14 CLIMAT years), Mainé-Soroa (3rd of 15) and Zinder (6th of 14, after a very wet June), and June at Maradi and Tahoua. Diffa’s 2026 CLIMAT is corrupt (447&nbsp;mm from 4 rain days) and unusable.</p>
  <p><strong>That largely vindicates the near-normal ENACTS MON zone mean</strong> — a wet west plus eastern/July pockets genuinely averages out. The open questions shift: why does CHIRPS’s gauge blend read the same season at the 15% line (its ingest may inherit the incomplete GTS daily stream), why is ERA5 so much drier than everything else, and — still worth asking IRI/DMN — how many stations fed the 2026 MON run. The structural lesson stands either way: <strong>a single zone-average trigger cannot represent a pocket drought;</strong> the per-department view (the <a href="../pockets/">drought-pockets page</a>) is the right instrument for 2026.</p>
</div>

<section class="prose">
  <h2><span class="sec">01 · THE OFFICIAL NUMBER</span>What the Maproom actually shows</h2>
  <p>The operational trigger surface is the IRI FBF Maproom (<a href="https://iridl.ldeo.columbia.edu/fbfmaproom2/niger">fbfmaproom2/niger</a>). Its observational indicator, <code>enacts-mon-spi-jj</code>, is the ENACTS <em>monitoring</em> product: DMN station data merged onto a CHIRP (satellite-only) background, averaged as per-pixel SPI over the national zone south of 17°N. Queried today through the Maproom’s export API:</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Quantity</th><th class="num">Value</th><th>Reading</th></tr></thead>
    <tbody>
      <tr><td>2026 Jun–Jul SPI (ENACTS MON)</td><td class="num">−0.120</td><td>16th driest of 36 (1991–2026)</td></tr>
      <tr><td>Threshold at 15% frequency</td><td class="num">−0.712</td><td>would need ~6th driest</td></tr>
      <tr><td>Threshold at 35% (endorsed PDF)</td><td class="num">−0.362</td><td>2026 misses this too</td></tr>
      <tr><td>CHIRP alone (MON’s satellite background)</td><td class="num">−0.008</td><td>near normal</td></tr>
      <tr><td>Station influence (MON − CHIRP), 2026</td><td class="num">−0.11</td><td>vs −0.75 in 2022, −0.39 in 2025</td></tr>
    </tbody>
  </table></div>
  <p>Two of the Maproom’s corroborating gauge datasets are simply not current: the pure DMN <code>station-spi-jj</code> series ends in <strong>2022</strong> and the final ENACTS product ends in <strong>2021</strong>. Only the MON product is live, and the gridded ENACTS datasets behind it are access-restricted on the Data Library — the export API is the public window.</p>
</section>

<figure>
  <p class="ftitle">Where Jun–Jul 2026 lands, dataset by dataset</p>
  <p class="fsub">percentile of 2026 within each dataset’s own 1991–2026 record · lower = drier</p>
  <div class="chartbox" id="chart-pctl"></div>
  <figcaption>Every dataset ranks the same season against its own history, so a constant bias cancels out. ERA5 and zone-masked CHIRPS sit at or below the 15% activation line; the official ENACTS MON indicator and its CHIRP background sit near normal; ARC2 (whose recent-year Sahel quality is widely doubted) calls 2026 wet. The disagreement spans 80 percentile points for the same rainfall season.</figcaption>
</figure>

<section class="prose">
  <h2><span class="sec">02 · WHY THE PROXIES DISAGREE</span>One satellite background, two station stories</h2>
  <p>CHIRP and CHIRPS share the same infrared satellite estimate; CHIRPS adds the Climate Hazards Center’s gauge blend. In a typical recent year that blend <em>adds</em> 15–30&nbsp;mm to the Niger Jun–Jul box mean (+55&nbsp;mm in 2024). In 2026 it <em>subtracted</em> 6&nbsp;mm — a swing of 25–35&nbsp;mm downward, entirely attributable to what the gauges reported. CHC’s published station lists confirm 13–14 Niger gauges were ingested in June and July 2026, the same synoptic set as in 2024–25. <strong>CHIRPS’s dry 2026 signal is gauge-driven, not a satellite artifact.</strong></p>
  <p>ERA5 is the loudest witness (2nd driest of 36) but also the least reliable for this zone: it assimilates no rain gauges, and against the Maproom’s own DMN station SPI (1991–2022) it correlates at just r&nbsp;≈&nbsp;0.59 — the weakest of everything we tested.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Dataset</th><th class="num">r vs DMN station SPI</th><th class="num">Spearman</th><th>Gauges used</th></tr></thead>
    <tbody>
      <tr><td>CHIRPS (zone mean, mm)</td><td class="num"><strong>0.90</strong></td><td class="num">0.89</td><td>~13 GTS synoptic</td></tr>
      <tr><td>ENACTS MON SPI (official)</td><td class="num">0.87</td><td class="num">0.88</td><td>DMN network</td></tr>
      <tr><td>ENACTS final SPI</td><td class="num">0.84</td><td class="num">0.85</td><td>DMN network (QC’d)</td></tr>
      <tr><td>CHIRP SPI (satellite only)</td><td class="num">0.66</td><td class="num">0.67</td><td>none</td></tr>
      <tr><td>ERA5 (zone mean, mm)</td><td class="num">0.59</td><td class="num">0.64</td><td>none</td></tr>
    </tbody>
  </table></div>
  <p>The historical benchmark cuts against dismissing the proxy: <strong>over 1991–2022, CHIRPS tracked Niger’s own station SPI as well as the official ENACTS MON product did.</strong> CHIRPS is not a poor cousin for this zone.</p>
</section>

<section class="prose">
  <h2><span class="sec">03 · THE GROUND TRUTH PROBLEM</span>What actual rain gauges say about 2026</h2>
  <p>First, the uncomfortable finding: <strong>no curated public gauge archive covers Jun–Jul 2026.</strong> GHCN-Daily has complete Niger precipitation through 2025 and then goes silent; GSOD and ISD end at 2025; Meteostat’s feed dies in March 2026. What remains is the GTS stream itself, which reaches the public in two forms — the daily synop reports, and the monthly <strong>CLIMAT</strong> summaries DMN compiles and transmits after each month (archived by OGIMET back to ~2008).</p>
  <p><strong>These two routes disagree, and the CLIMAT monthlies win.</strong> The first version of this note summed the daily synop stream, which only captured ~70% of days — and the missing days carried rain, so the eastern totals came out far too low (Zinder read 82&nbsp;mm against a CLIMAT-complete 211; Magaria 97 vs 186; Mainé-Soroa 33 vs 90). The complete monthly record, below, is the better gauge truth — with its own defects: Diffa’s July 2026 CLIMAT transmits 447&nbsp;mm from 4 rain days (garbage), and Maradi’s June transmits exactly 0.0&nbsp;mm (doubtful — the daily stream shows June rain there).</p>
</section>

<figure>
  <p class="ftitle">DMN gauges, Jun–Jul CLIMAT totals: 2026 vs each station’s full CLIMAT record</p>
  <p class="fsub">stations ordered west → east · monthly CLIMAT reports via OGIMET, 2008–2026 · mm · Diffa excluded (corrupt 2026 value)</p>
  <div class="legend">
    <span class="key"><span class="swatch" style="background:var(--s1)"></span>mean of complete CLIMAT years (8–12 per station)</span>
    <span class="key"><span class="swatch" style="background:var(--s2)"></span>2026 (complete months)</span>
  </div>
  <div class="chartbox" id="chart-stations"></div>
  <figcaption>Seasonal totals are normal to above normal at most stations — the west (Tillabéry +70%, Niamey, Dosso) clearly wet. The drought hides inside the season: <strong>July alone</strong> was 2nd driest of 14 CLIMAT years at Magaria, 3rd of 15 at Mainé-Soroa, and 6th of 14 at Zinder (whose very wet June rescues its seasonal total); <strong>June</strong> was severely dry at Tahoua and (per a doubtful 0.0&nbsp;mm report) Maradi. This “pockets in space and time” picture matches FEWS NET’s July monitor — deficits concentrated in central-southern Niger — and the per-department return periods on the <a href="../pockets/">drought-pockets page</a>, where most gauge RPs sit below 2.5 and the strong signals are departmental, not national.</figcaption>
</figure>

<section class="prose">
  <h2><span class="sec">04 · THE REMAINING PUZZLE</span>If the gauges say “pockets”, who is the outlier?</h2>
  <p>The corrected gauge record changes the shape of the question. A wet west offsetting eastern and July-only deficits is <em>consistent</em> with ENACTS MON’s near-normal zone mean (−0.12) — the official indicator no longer looks like it ignored its own inputs. What now needs explaining is the other side: why does CHIRPS place the same season at the 15% line, and ERA5 at the 6th percentile? A plausible mechanism for CHIRPS is that CHC’s blend ingests the GTS <em>daily</em> stream — the same incomplete feed that biased the first version of this note dry — rather than the complete monthly CLIMATs. ERA5, with no gauge input and the weakest historical correlation, is most simply read as an outlier. The MON-vs-CHIRP station pull is still worth watching, though: 2026’s pull (−0.11) is small next to recent years, and station counts in the MON run remain unpublished.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Year</th><th class="num">ENACTS MON</th><th class="num">CHIRP only</th><th class="num">Station pull (MON−CHIRP)</th></tr></thead>
    <tbody>
      <tr><td>2021</td><td class="num">+0.25</td><td class="num">+0.08</td><td class="num">+0.17</td></tr>
      <tr><td>2022</td><td class="num">−0.79</td><td class="num">−0.04</td><td class="num"><strong>−0.75</strong></td></tr>
      <tr><td>2023</td><td class="num">−0.36</td><td class="num">−0.06</td><td class="num">−0.30</td></tr>
      <tr><td>2024</td><td class="num">+1.25</td><td class="num">+1.07</td><td class="num">+0.19</td></tr>
      <tr><td>2025</td><td class="num">+0.36</td><td class="num">+0.75</td><td class="num">−0.39</td></tr>
      <tr><td>2026</td><td class="num">−0.12</td><td class="num">−0.01</td><td class="num"><strong>−0.11</strong></td></tr>
    </tbody>
  </table></div>
  <p>In 2022 the station merge pulled the index down by three-quarters of an SPI unit — that pull is what activated the framework. In 2026 the pull was 0.11 — which the corrected gauge record suggests may simply be the truth (wet west, dry pockets), though two residual checks remain worthwhile:</p>
  <ol class="talk">
    <li><strong>Station input to the 2026 run.</strong> The endorsed 2024 framework specifies falling back to satellite-only CHIRP if ≥20% of stations are missing by 7 August. Asking IRI/DMN for the station count costs nothing and settles whether the small pull reflects real conditions or thin input.</li>
    <li><strong>Dilution by design.</strong> The indicator is an equal-weight average of per-pixel SPI over the whole zone south of 17°N. That is exactly why a pocket drought — Zinder/Magaria/Mainé-Soroa’s failed July, a failed June around Maradi/Tahoua — cannot move it much. Working as designed is not the same as measuring what matters for a departmental-scale food-security shock.</li>
  </ol>
  <div class="callout"><strong>A stability caveat worth knowing before anyone quotes old numbers:</strong> the MON SPI series is revised after publication. Our April 2026 Maproom export shows 2022 at −0.51 and 2025 at +0.47; the live Maproom today shows −0.79 and +0.36 for the same years. SPI is refit as the record extends and as late station data arrives — so value-locked thresholds and backtests drift, and screenshots from different months will disagree.</div>
</section>

<section class="prose">
  <h2><span class="sec">05 · THE COUNTEREXAMPLE</span>2022 cuts the other way</h2>
  <p>Before concluding ENACTS is broken, note that the exact mirror image happened in 2022 — the framework’s one real observational activation. ENACTS MON read −0.79 (4th driest on record) and DMN stations agreed (−0.58); our CHIRPS and ERA5 zone means put 2022 <em>mid-pack</em> (16th–17th of 35). If the argument this year is “CHIRPS says 2026 should have triggered,” the symmetric argument is “CHIRPS says 2022 shouldn’t have.” The 2022 drought was concentrated in the southwest; 2026’s is in the east. <strong>A single zone-wide average is fragile to regional droughts, and which dataset “sees” a given drought depends on where its information sources sit.</strong> That — not any one product being wrong — is the structural finding.</p>
</section>

<section class="prose">
  <h2><span class="sec">06 · POSITIONING</span>What to say under scrutiny</h2>
  <ol class="talk">
    <li><strong>The process was followed and the call wasn’t close on its own terms.</strong> The designated indicator, computed by the designated operator on the designated platform, read the 44th percentile against a 15% threshold. It would not have activated even at the endorsed 35% threshold. There is no version of “it just missed.”</li>
    <li><strong>Niger’s own monthly gauge reports support a “pockets” reading, not a zone-wide drought.</strong> Most stations’ Jun–Jul totals were normal to above normal (the west clearly wet); severe deficits were real but localized — a failed July around Zinder, Magaria and Mainé-Soroa, a failed June around Maradi and Tahoua — matching FEWS NET’s “deficits in central-southern Niger.” A zone-average indicator reading near-normal over that pattern is arithmetic, not malfunction.</li>
    <li><strong>Dataset disagreement is structural and symmetric.</strong> CHIRPS puts the zone at the 15% line and ERA5 lower still, while ENACTS, CHIRP and the CLIMAT gauges read near-normal; in 2022 the disagreement ran the other way (ENACTS triggered, CHIRPS/ERA5 mid-pack). Which product “sees” a given drought depends on where its information sits — which is why no single zone-average product should carry the whole decision.</li>
    <li><strong>Two technical checks are still open, and we are pursuing them:</strong> the station count behind the 2026 MON run (the framework’s own ≥20%-missing CHIRP fallback rule makes this a fair question), and why CHIRPS’s gauge blend diverges from the complete CLIMAT record — plausibly because it ingests the incomplete GTS daily stream.</li>
    <li><strong>For the 2027 redesign this argues for sub-zonal resilience, not dataset loyalty:</strong> 2026 (an eastern pocket drought the zone mean averaged away) and 2022 (a southwestern one it caught) together show the binding constraint is spatial aggregation more than dataset choice. Departmental return periods — the approach on the <a href="../pockets/">pockets page</a> — plus a multi-dataset check (CHIRPS tracks DMN gauges historically as well as ENACTS MON does, r ≈ 0.90 vs 0.87) would catch what either misses alone, at the cost of a more complex trigger to govern.</li>
  </ol>
  <h2><span class="sec">07 · OPEN QUESTIONS FOR IRI / DMN</span>The checklist</h2>
  <ul class="qs">
    <li>How many DMN stations were merged into the <strong>2026 Jun–Jul ENACTS MON</strong> run, and with what cutoff date? Was the ≥20%-missing CHIRP fallback rule evaluated?</li>
    <li>Can the <code>station-spi-jj</code> series (ends 2022) and final ENACTS (ends 2021) be brought current on the Maproom, so gauge-vs-product checks stay possible?</li>
    <li>What is the revision policy for the MON SPI series? (We observe historical values shifting between April and August 2026 exports.)</li>
    <li>Can IRI publish the MON gridded anomaly map for Jun–Jul 2026, to confirm whether the eastern deficit appears spatially but averages out?</li>
  </ul>
  <p class="small"><strong>Method notes.</strong> Maproom values from the <code>fbfmaproom2/niger/export</code> API (national region, 1991–2026, <code>include_upcoming</code>). CHIRP/CHIRPS/ARC2 series computed on the IRI Data Library over 0–16°E, 11–17°N; zone-masked CHIRPS/ERA5 from this repo’s <code>docs/rainfall</code> pipeline (Niger south of 17°N). Gauge figures are DMN monthly CLIMAT reports decoded from OGIMET (2008–2026, 8–12 complete Jun+Jul years per station; the repo’s <code>exploration/pockets_fetch_gauges.py</code> pipeline); per-station July ranks computed within each station’s own CLIMAT Julys. Known bad values: Diffa Jul 2026 (447&nbsp;mm), Maradi Jun 2026 (0.0&nbsp;mm, doubtful). <em>Revision 1 Sep 2026:</em> the first version of this note summed GTS daily synop reports (~70% day coverage) and overstated the eastern seasonal deficits; the CLIMAT monthlies supersede those figures. Historical correlations computed against the Maproom’s DMN <code>station-spi-jj</code> series, 1991–2022. FEWS NET: <a href="https://fews.net/west-africa/seasonal-monitor/july-2026">West Africa seasonal monitor, July 2026</a>. Companion view: <a href="../pockets/">2026 drought-pockets page</a> (per-department RPs, HNRP severity overlay).</p>
</section>
</div>

<div class="tooltip" id="tip"></div>

<script>
(function(){
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const tip = document.getElementById('tip');
  function showTip(ev, html){
    tip.innerHTML = html; tip.style.opacity = 1;
    const pad = 14;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    const r = tip.getBoundingClientRect();
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - pad;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - pad;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hideTip(){ tip.style.opacity = 0; }

  /* ---------- Chart 1: percentile dot plot ---------- */
  const pdata = [
    {name:'ERA5 · zone mean',        p:6,  note:'2nd driest of 36 · no gauge input · weakest gauge correlation (r 0.59)'},
    {name:'CHIRPS · zone mean',      p:17, note:'6th driest of 36 — exactly the 15% rank · 13–14 Niger gauges ingested'},
    {name:'CHIRPS · wide box',       p:28, note:'10th of 36 over 0–16°E — the dry signal concentrates inside Niger'},
    {name:'ENACTS MON · official',   p:44, note:'−0.120 SPI · 16th of 36 · the trigger dataset', official:true},
    {name:'CHIRP · satellite only',  p:44, note:'−0.008 SPI · MON’s own background, no stations'},
    {name:'ARC2 · NOAA CPC',         p:86, note:'6th wettest of 44 · recent-year Sahel quality widely doubted'},
  ];
  (function(){
    const W = 860, rowH = 44, padL = 208, padR = 30, padT = 34, padB = 34;
    const H = padT + padB + rowH * pdata.length;
    const x = p => padL + (W - padL - padR) * p / 100;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="min-width:640px" role="img" aria-label="Dot plot of the 2026 percentile in six rainfall datasets">`;
    for (const g of [0,25,50,75,100]) {
      s += `<line x1="${x(g)}" y1="${padT-8}" x2="${x(g)}" y2="${H-padB}" stroke="var(--grid)" stroke-width="1"/>`;
      s += `<text x="${x(g)}" y="${H-padB+18}" font-size="11" fill="var(--muted)" text-anchor="middle">${g}</text>`;
    }
    s += `<text x="${x(50)}" y="${H-6}" font-size="11" fill="var(--muted)" text-anchor="middle">percentile of 2026 in the dataset’s own 1991–2026 record</text>`;
    /* threshold lines */
    s += `<line x1="${x(15)}" y1="${padT-8}" x2="${x(15)}" y2="${H-padB}" stroke="var(--s2)" stroke-width="1.6"/>`;
    s += `<text x="${x(15)}" y="${padT-14}" font-size="11" fill="var(--s2)" text-anchor="middle">15% threshold</text>`;
    s += `<line x1="${x(35)}" y1="${padT-8}" x2="${x(35)}" y2="${H-padB}" stroke="var(--s2)" stroke-width="1.4" stroke-dasharray="4 4"/>`;
    s += `<text x="${x(35)}" y="${padT-14}" font-size="11" fill="var(--s2)" text-anchor="middle" opacity=".8">35% (endorsed)</text>`;
    pdata.forEach((d,i)=>{
      const cy = padT + rowH*i + rowH/2;
      s += `<text x="${padL-14}" y="${cy+4}" font-size="12.5" fill="var(--ink-2)" text-anchor="end">${d.name}</text>`;
      s += `<line x1="${padL}" y1="${cy}" x2="${x(d.p)}" y2="${cy}" stroke="var(--axis)" stroke-width="1.2"/>`;
      const r = d.official ? 8 : 6;
      const ring = d.official ? `<circle cx="${x(d.p)}" cy="${cy}" r="${r+4}" fill="none" stroke="var(--s1)" stroke-width="1.4" opacity=".55"/>` : '';
      s += ring + `<circle class="pdot" data-i="${i}" cx="${x(d.p)}" cy="${cy}" r="${r}" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>`;
      s += `<text x="${x(d.p)+ (d.p>90?-16:14)}" y="${cy+4}" font-size="12" fill="var(--ink)" font-weight="${d.official?600:400}" text-anchor="${d.p>90?'end':'start'}">${d.p}%</text>`;
    });
    s += `</svg>`;
    const el = document.getElementById('chart-pctl');
    el.innerHTML = s;
    el.querySelectorAll('.pdot').forEach(dot=>{
      const d = pdata[+dot.dataset.i];
      const enter = ev => showTip(ev, `<strong>${d.name}</strong><br>2026 at the ${d.p}th percentile<br>${d.note}`);
      dot.addEventListener('mousemove', enter);
      dot.addEventListener('mouseleave', hideTip);
    });
  })();

  /* ---------- Chart 2: station dumbbells ---------- */
  const sdata = [
    {name:'Tillabéry',     v26:310, ref:182, n:9,  note:'well above normal'},
    {name:'Niamey',        v26:283, ref:200, n:12, note:'above normal'},
    {name:'Dosso',         v26:260, ref:199, n:8,  note:'above normal'},
    {name:'Gaya',          v26:284, ref:280, n:11, note:'normal'},
    {name:'Birni-N’Konni', v26:212, ref:232, n:11, note:'slightly below normal'},
    {name:'Tahoua',        v26:171, ref:246, n:9,  note:'June very dry; July wet'},
    {name:'Maradi',        v26:187, ref:214, n:11, note:'June CLIMAT = 0.0 mm (doubtful); July normal'},
    {name:'Magaria',       v26:186, ref:227, n:10, low:true, note:'July 125 mm — 2nd driest of 14 CLIMAT Julys'},
    {name:'Zinder',        v26:211, ref:220, n:9,  low:true, note:'July 112 mm — 6th driest of 14; June very wet'},
    {name:'Gouré',         v26:146, ref:206, n:11, note:'below normal'},
    {name:'Mainé-Soroa',   v26:90,  ref:126, n:10, low:true, note:'July 33 mm — 3rd driest of 15 CLIMAT Julys'},
    {name:'N’Guigmi',      v26:75,  ref:109, n:11, note:'below normal'},
  ];
  (function(){
    const W = 860, rowH = 34, padL = 150, padR = 84, padT = 26, padB = 40;
    const H = padT + padB + rowH * sdata.length;
    const maxV = 320;
    const x = v => padL + (W - padL - padR) * v / maxV;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="min-width:640px" role="img" aria-label="Dumbbell chart of Jun–Jul CLIMAT rainfall totals at 12 Niger stations, 2026 versus each station's CLIMAT-record mean">`;
    for (const g of [0,100,200,300]) {
      s += `<line x1="${x(g)}" y1="${padT-6}" x2="${x(g)}" y2="${H-padB}" stroke="var(--grid)" stroke-width="1"/>`;
      s += `<text x="${x(g)}" y="${H-padB+18}" font-size="11" fill="var(--muted)" text-anchor="middle">${g}</text>`;
    }
    s += `<text x="${x(150)}" y="${H-8}" font-size="11" fill="var(--muted)" text-anchor="middle">Jun–Jul precipitation (mm)</text>`;
    sdata.forEach((d,i)=>{
      const cy = padT + rowH*i + rowH/2;
      s += `<text x="${padL-12}" y="${cy+4}" font-size="12.5" fill="var(--ink-2)" text-anchor="end" font-weight="${d.low?600:400}">${d.name}</text>`;
      s += `<line class="srow" data-i="${i}" x1="${x(Math.min(d.v26,d.ref))}" y1="${cy}" x2="${x(Math.max(d.v26,d.ref))}" y2="${cy}" stroke="var(--axis)" stroke-width="2"/>`;
      s += `<circle class="srow" data-i="${i}" cx="${x(d.ref)}" cy="${cy}" r="6" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>`;
      s += `<circle class="srow" data-i="${i}" cx="${x(d.v26)}" cy="${cy}" r="6" fill="var(--s2)" stroke="var(--surface)" stroke-width="2"/>`;
      if (d.low) s += `<text x="${x(Math.max(d.v26,d.ref))+12}" y="${cy+4}" font-size="11.5" fill="var(--s2)" font-weight="500">dry July</text>`;
    });
    s += `</svg>`;
    const el = document.getElementById('chart-stations');
    el.innerHTML = s;
    el.querySelectorAll('.srow').forEach(m=>{
      const d = sdata[+m.dataset.i];
      const enter = ev => showTip(ev, `<strong>${d.name}</strong><br>2026 Jun–Jul: ${d.v26} mm · CLIMAT-record mean (${d.n} yrs): ${d.ref} mm (${Math.round(100*(d.v26/d.ref-1))>=0?'+':''}${Math.round(100*(d.v26/d.ref-1))}%)<br>${d.note}`);
      m.addEventListener('mousemove', enter);
      m.addEventListener('mouseleave', hideTip);
    });
  })();
})();
</script>

</body>
</html>
"""


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(PAGE)
    print(f"wrote {OUT} ({len(PAGE):,} bytes)")


if __name__ == "__main__":
    main()
