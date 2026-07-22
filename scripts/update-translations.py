#!/usr/bin/env python3
"""Surface new/changed source strings into the German catalogues.

Extracts the gettext POT from the docs, merges it into each translated
``docs/locale/de_DE/LC_MESSAGES/*.po`` via polib, and normalises the result
back to the committed format so an unchanged source produces no diff. New or
changed msgids appear as untranslated (or fuzzy) entries ready for a translator;
the script prints those it surfaced.

Run with the docs toolchain, e.g. ``uv run --group docs python
scripts/update-translations.py``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import polib

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
POT_DIR = DOCS / "_build" / "gettext"
LOCALE = DOCS / "locale" / "de_DE" / "LC_MESSAGES"
LANGUAGE = "de_DE"

# Pages deliberately left in English -- never surface them.
SKIP = {"changelog", "contributors"}

# The only header fields the committed catalogues keep; everything sphinx/polib
# would otherwise add (POT-Creation-Date, Last-Translator, Generated-By, ...) is
# volatile head matter that would churn on every run, so it is stripped.
CANONICAL_HEADER = (
    "Project-Id-Version",
    "Language",
    "MIME-Version",
    "Content-Type",
    "Content-Transfer-Encoding",
    "Plural-Forms",
)


def extract_pot() -> None:
    """Build the gettext catalogues into ``docs/_build/gettext``."""
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "gettext", ".", "_build/gettext"],
        cwd=DOCS,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit("gettext extraction failed")


def _canonical_occurrences(occurrences: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Reduce POT occurrences to stable, line-free navigation hints.

    Line numbers drift on every doc edit, so they are dropped -- the file (or,
    for autodoc, the ``of <object>`` name) alone is the hint. Also drops the
    ``<module>.py:docstring`` autodoc path token and de-duplicates, so a string
    used on several lines collapses to a single occurrence.
    """
    out: list[tuple[str, str]] = []
    for path, _line in occurrences:
        if path.endswith(":docstring"):
            continue
        occ = (path, "")
        if occ not in out:
            out.append(occ)
    return out


def strip_header(po: polib.POFile) -> None:
    """Drop the volatile head matter ``merge`` reintroduces."""
    for key in list(po.metadata):
        if key not in CANONICAL_HEADER:
            del po.metadata[key]


def surfaced(po: polib.POFile) -> list[str]:
    """msgids that still need a translator after the merge."""
    return [e.msgid for e in po if not e.obsolete and (not e.translated() or "fuzzy" in e.flags)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="reuse an existing docs/_build/gettext instead of re-extracting",
    )
    args = parser.parse_args()

    if not args.skip_build:
        extract_pot()

    catalogues = sorted(p for p in LOCALE.glob("*.po") if p.stem not in SKIP)
    seen = {p.stem for p in catalogues} | SKIP
    pending: dict[str, list[str]] = {}

    for po_path in catalogues:
        pot_path = POT_DIR / f"{po_path.stem}.pot"
        if not pot_path.exists():
            sys.stderr.write(f"note: {po_path.name} has no POT (page removed?)\n")
            continue
        po = polib.pofile(str(po_path))
        po.merge(polib.pofile(str(pot_path)))
        for entry in po:
            entry.occurrences = _canonical_occurrences(entry.occurrences)
        strip_header(po)
        po.save(str(po_path))
        if todo := surfaced(po):
            pending[po_path.stem] = todo

    for pot_path in sorted(POT_DIR.glob("*.pot")):
        if pot_path.stem not in seen:
            sys.stderr.write(
                f"note: {pot_path.stem} has source strings but no {LANGUAGE} "
                f"catalogue -- not surfaced\n"
            )

    for page, msgids in pending.items():
        print(f"{page}: {len(msgids)} to translate")
        for msgid in msgids:
            print(f"  {msgid[:100]!r}")


if __name__ == "__main__":
    main()
