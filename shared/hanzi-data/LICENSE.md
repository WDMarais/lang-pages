# Stroke data — license & provenance

The per-character JSON files in this directory (`strokes` outlines + `medians`)
come from the **Make-Me-a-Hanzi** project, distributed via the `hanzi-writer-data`
package, and are derived from the **Arphic PL UKai** font.

- **Graphical stroke data** (the glyph outlines): **Arphic Public License (APL)**.
  Free to use, modify, and redistribute, including commercially, provided this
  license notice travels with the data. The APL's copyleft applies to the glyph
  data and direct derivatives of it — NOT to independent software that merely
  consumes it (rendering/ordering/orchestration code is unaffected).
- **Non-graphical data** (where present): LGPL, per Make-Me-a-Hanzi.

Some files are **lifted** from a source character rather than downloaded whole:
a single stroke (or two) is extracted from a common character and recentred to
the tile, for glyphs absent from the dataset (CJK-Strokes block, katakana). These
remain APL derivatives of the same Arphic data. Both downloading and lifting are
handled by `./fetch.py` — see its docstring for the exact per-glyph commands.

The **HanziWriter** library in `../vendor/hanzi-writer.min.js` is separate and
licensed **MIT** (https://github.com/chanind/hanzi-writer).

Sources:
- https://github.com/skishore/makemeahanzi
- https://github.com/chanind/hanzi-writer
- Arphic Public License: https://www.freedesktop.org/wiki/Arphic_Public_License/
