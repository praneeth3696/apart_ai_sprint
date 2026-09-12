"""
assemble.py

Concatenates the report sections in submission order into report/REPORT.md and
estimates the page count against the 8-page limit.

Sections are separate files so they can be drafted, reviewed and committed
independently; this is the only place the running order lives.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ORDER = [
    "00_abstract.md",
    "01_introduction.md",
    "06_related_work.md",
    "02_methodology.md",
    "03_results.md",
    "04_discussion.md",
    "05_limitations_dualuse.md",
]
# The official template is still unpublished ("Coming Soon" on the Guidelines
# tab), so page count is a range, not a number. A single-column template runs
# ~500 words/page; a two-column academic one ~750. We report both and size
# against the pessimistic end.
WORDS_PER_PAGE = 500
WORDS_PER_PAGE_DENSE = 750
FIGURE_PAGES = 0.8          # Figures 1 and 2


def words(text: str) -> int:
    text = re.sub(r"^\s*>.*$", "", text, flags=re.M)      # blockquotes still count
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’./%-]*", text))


def main() -> int:
    parts, rows, total = [], [], 0
    for name in ORDER:
        p = HERE / name
        if not p.is_file():
            print(f"MISSING: {name}", file=sys.stderr)
            continue
        t = p.read_text(encoding="utf-8")
        w = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’./%-]*", t))
        total += w
        rows.append((name, w))
        parts.append(t.rstrip() + "\n")

    out = HERE / "REPORT.md"
    out.write_text("\n\n".join(parts), encoding="utf-8")

    print(f"{'section':<32} {'words':>7} {'1-col':>7} {'2-col':>7}")
    print("-" * 58)
    for name, w in rows:
        print(f"{name:<32} {w:>7} {w / WORDS_PER_PAGE:>7.1f} "
              f"{w / WORDS_PER_PAGE_DENSE:>7.1f}")
    print("-" * 58)
    print(f"{'TOTAL (text)':<32} {total:>7} {total / WORDS_PER_PAGE:>7.1f} "
          f"{total / WORDS_PER_PAGE_DENSE:>7.1f}")
    appendix = dict(rows).get("05_limitations_dualuse.md", 0)
    body = total - appendix

    def span(w):
        return (w / WORDS_PER_PAGE_DENSE + FIGURE_PAGES,
                w / WORDS_PER_PAGE + FIGURE_PAGES)

    lo_all, hi_all = span(total)
    lo_body, hi_body = span(body)
    print(f"{'+ figures':<32} {'':>7} {hi_all:>7.1f} {lo_all:>7.1f}")
    print()
    print("The 8-page limit turns on one unknown: the guidelines list the")
    print("Limitations and Dual-Use appendix as a SEPARATE required deliverable,")
    print("so it may well sit outside the page count. Both readings:")
    print()
    for label, (lo, hi) in (("including the appendix", (lo_all, hi_all)),
                            ("body only (appendix separate)", (lo_body, hi_body))):
        verdict = ("fits either way" if hi <= 8 else
                   "fits if two-column" if lo <= 8 else "OVER in both — cut")
        print(f"  {label:<32} {lo:>4.1f}-{hi:<4.1f} pages   {verdict}")
    print()
    print("  Confirm against the official template when it is published.")
    print("  Cut order if needed is in report/README.md; the appendix is scored,")
    print("  so cut it last.")
    print(f"\nwrote {out.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
