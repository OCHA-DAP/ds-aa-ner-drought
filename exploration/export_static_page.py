"""Regenerate the static snapshot pages served at /static/ on GitHub Pages.

Runs ``marimo export html`` on the rolling-threshold app (which executes it at
its default slider values — forecast 35%, observational 15%) once per language
(EN at docs/static/, FR at docs/static/fr/ via ``-- -lang fr``), then applies
the static-page post-processing: page title, snapshot banner with an EN | FR
toggle, and locking the interactive controls.

Usage:
    uv run python exploration/export_static_page.py

Loads the source CSV from Azure blob via ocha-stratus, so blob credentials
must be available. Commit the regenerated ``docs/static/`` tree on the
``iri-trend`` branch to deploy.
"""

import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "exploration" / "rolling_threshold_marimo.py"

FR_MONTHS = [
    "",
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

LANGS = {
    "en": {
        "out": ROOT / "docs" / "static" / "index.html",
        "args": [],
        "title": "Niger Drought AA Trigger — Static Snapshot",
        "explorer_href": "../",
        "toggle": (
            '<strong>EN</strong> | <a href="fr/" style="color:#aed6f1;">FR</a>'
        ),
    },
    "fr": {
        "out": ROOT / "docs" / "static" / "fr" / "index.html",
        "args": ["--", "-lang", "fr"],
        "title": "Déclencheur AA sécheresse Niger — instantané statique",
        "explorer_href": "../../",
        "toggle": (
            '<a href="../" style="color:#aed6f1;">EN</a> | <strong>FR</strong>'
        ),
    },
}

LOCK_CSS = (
    "<style>marimo-slider, marimo-dropdown, marimo-ui-element "
    "{ pointer-events: none !important; }</style>"
)


def banner(lang: str, cfg: dict) -> str:
    today = datetime.date.today()
    if lang == "fr":
        text = (
            "Instantané statique aux <strong>seuils par défaut</strong> "
            f"(prévision 35%, observation 15%) — exporté le "
            f"{today.day} {FR_MONTHS[today.month]} {today.year}. "
            "Les curseurs de cette page ne sont pas interactifs ; "
            f'<a href="{cfg["explorer_href"]}" style="color:#aed6f1;">'
            "ouvrir l’explorateur interactif</a>."
        )
    else:
        text = (
            "Static snapshot at <strong>default thresholds</strong> "
            f"(forecast 35%, observational 15%) — exported "
            f"{today.strftime('%-d %B %Y')}. "
            "Sliders on this page are not interactive; "
            f'<a href="{cfg["explorer_href"]}" style="color:#aed6f1;">'
            "open the interactive explorer</a>."
        )
    return (
        '<div style="background:#1a5276;color:#fff;padding:0.6rem 1rem;'
        "font-family:system-ui,sans-serif;font-size:0.9rem;text-align:center;"
        'position:sticky;top:0;z-index:9999;">'
        f'<span style="float:right;letter-spacing:0.05em;">{cfg["toggle"]}</span>'
        f"{text}</div>"
    )


def main() -> None:
    for lang, cfg in LANGS.items():
        out = cfg["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "marimo",
                "export",
                "html",
                "--no-include-code",
                "-f",
                "-o",
                str(out),
                str(NOTEBOOK),
                *cfg["args"],
            ],
            check=True,
        )

        s = out.read_text()
        s = s.replace(
            "<title>rolling threshold marimo</title>",
            f"<title>{cfg['title']}</title>",
            1,
        )
        s = s.replace("<body>", "<body>" + banner(lang, cfg), 1)
        n_locked = s.count("data-disabled='false'")
        s = s.replace("data-disabled='false'", "data-disabled='true'")
        s = s.replace("</head>", LOCK_CSS + "</head>", 1)
        if lang != "en":
            s = s.replace(
                "<html lang='en'>", f"<html lang='{lang}'>", 1
            ).replace('<html lang="en">', f'<html lang="{lang}">', 1)
        out.write_text(s)
        print(
            f"[{lang}] Wrote {out} ({len(s):,} bytes); "
            f"locked {n_locked} controls."
        )


if __name__ == "__main__":
    main()
