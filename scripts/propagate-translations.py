#!/usr/bin/env python3
"""Propagate repeated translations across a language's catalogues.

A string translated in one ``docs/locale/<lang>/LC_MESSAGES/*.po`` is copied
into every other catalogue of the same language where the identical msgid is
still untranslated. There is no separate compendium file -- the translated
catalogues themselves are the translation memory. This is idempotent: a set
that is already fully propagated produces no change.

Only unambiguous strings propagate. If the same msgid is translated two
different ways across a language's catalogues, it is left untouched and
reported, so a deliberate per-page nuance is never overwritten. Existing
(non-empty) translations are never clobbered; fuzzy entries are left alone.

Pass page stems to restrict which catalogues get filled (the memory is still
built from every page); omit them to fill all. ``--language`` restricts to one
locale; ``--dry-run`` reports without writing.

Run with the docs toolchain, e.g. ``uv run --group docs python
scripts/propagate-translations.py`` or ``... propagate-translations.py qrcode``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polib

REPO = Path(__file__).resolve().parent.parent
LOCALES_ROOT = REPO / "docs" / "locale"


def discover_locales() -> list[Path]:
    """The ``LC_MESSAGES`` dir of every locale under ``docs/locale``."""
    return sorted(lc for p in LOCALES_ROOT.iterdir() if (lc := p / "LC_MESSAGES").is_dir())


def build_memory(catalogues: list[polib.POFile]) -> tuple[dict[str, str], set[str]]:
    """Map each msgid to its translation, keeping only unambiguous ones.

    Returns ``(memory, conflicts)``; ``conflicts`` are msgids seen with more
    than one distinct translation and therefore excluded from ``memory``.
    """
    seen: dict[str, set[str]] = {}
    for po in catalogues:
        for entry in po:
            if entry.obsolete or not entry.msgid or not entry.msgstr:
                continue
            if "fuzzy" in entry.flags:
                continue
            seen.setdefault(entry.msgid, set()).add(entry.msgstr)
    conflicts = {msgid for msgid, values in seen.items() if len(values) > 1}
    memory = {msgid: next(iter(v)) for msgid, v in seen.items() if len(v) == 1}
    return memory, conflicts


def propagate(locale_dir: Path, only: set[str], dry_run: bool) -> tuple[int, set[str]]:
    """Fill untranslated entries in one locale from its own translated ones."""
    catalogues = {path: polib.pofile(str(path)) for path in sorted(locale_dir.glob("*.po"))}
    memory, conflicts = build_memory(list(catalogues.values()))

    filled = 0
    for path, po in catalogues.items():
        if only and path.stem not in only:
            continue
        changed = False
        for entry in po:
            if entry.obsolete or not entry.msgid or entry.msgstr or "fuzzy" in entry.flags:
                continue
            translation = memory.get(entry.msgid)
            if translation is not None:
                entry.msgstr = translation
                changed = True
                filled += 1
                print(f"  {path.name}: {entry.msgid[:70]!r}")
        if changed and not dry_run:
            po.save(str(path))
    return filled, conflicts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pages",
        nargs="*",
        help="only fill these page stems (e.g. qrcode ean13); default is all pages",
    )
    parser.add_argument(
        "--language",
        help="only this locale (e.g. fr_FR); default is every locale under docs/locale",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be propagated without writing",
    )
    args = parser.parse_args()

    locales = discover_locales()
    if args.language:
        locales = [lc for lc in locales if lc.parent.name == args.language]
        if not locales:
            raise SystemExit(f"no catalogue dir for language {args.language!r}")

    only = set(args.pages)
    for locale_dir in locales:
        lang = locale_dir.parent.name
        filled, conflicts = propagate(locale_dir, only, args.dry_run)
        verb = "would fill" if args.dry_run else "filled"
        plural = "y" if filled == 1 else "ies"
        print(f"{lang}: {verb} {filled} untranslated entr{plural}")
        if conflicts:
            sys.stderr.write(
                f"note: {lang}: {len(conflicts)} msgid(s) translated inconsistently "
                f"across pages -- not propagated:\n"
            )
            for msgid in sorted(conflicts):
                sys.stderr.write(f"  {msgid[:80]!r}\n")


if __name__ == "__main__":
    main()
