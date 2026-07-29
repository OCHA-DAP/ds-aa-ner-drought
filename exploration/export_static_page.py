"""Regenerate the static snapshot page served at /static/ on GitHub Pages.

Runs ``marimo export html`` on the rolling-threshold app (which executes it at
its default slider values — forecast 35%, observational 15%), then applies the
static-page post-processing: page title, snapshot banner, and locking the
interactive controls.

Usage:
    uv run python exploration/export_static_page.py

Loads the source CSV from Azure blob via ocha-stratus, so blob credentials
must be available. Commit the regenerated ``docs/static/index.html`` on the
``iri-trend`` branch to deploy.
"""

import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "exploration" / "rolling_threshold_marimo.py"
OUT = ROOT / "docs" / "static" / "index.html"

TITLE = "Niger Drought AA Trigger — Static Snapshot"
LOCK_CSS = (
    "<style>marimo-slider, marimo-dropdown, marimo-ui-element "
    "{ pointer-events: none !important; }</style>"
)


def banner(date_str: str) -> str:
    return (
        '<div style="background:#1a5276;color:#fff;padding:0.6rem 1rem;'
        "font-family:system-ui,sans-serif;font-size:0.9rem;text-align:center;"
        'position:sticky;top:0;z-index:9999;">'
        "Static snapshot at <strong>default thresholds</strong> "
        f"(forecast 35%, observational 15%) — exported {date_str}. "
        "Sliders on this page are not interactive; "
        '<a href="../" style="color:#aed6f1;">open the interactive explorer</a>.'
        "</div>"
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
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
            str(OUT),
            str(NOTEBOOK),
        ],
        check=True,
    )

    s = OUT.read_text()
    s = s.replace(
        "<title>rolling threshold marimo</title>", f"<title>{TITLE}</title>", 1
    )
    date_str = datetime.date.today().strftime("%-d %B %Y")
    s = s.replace("<body>", "<body>" + banner(date_str), 1)
    n_locked = s.count("data-disabled='false'")
    s = s.replace("data-disabled='false'", "data-disabled='true'")
    s = s.replace("</head>", LOCK_CSS + "</head>", 1)
    OUT.write_text(s)
    print(f"Wrote {OUT} ({len(s):,} bytes); locked {n_locked} controls.")


if __name__ == "__main__":
    main()
