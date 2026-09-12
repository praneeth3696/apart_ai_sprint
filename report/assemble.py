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
    "06_related_work_STUB.md",
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
    lo = total / WORDS_PER_PAGE_DENSE + FIGURE_PAGES
    hi = total / WORDS_PER_PAGE + FIGURE_PAGES
    print(f"{'+ figures':<32} {'':>7} {hi:>7.1f} {lo:>7.1f}")
    print()
    print(f"8-page limit: {'OK in both' if hi <= 8 else ('OK if two-column' if lo <= 8 else 'OVER in both — cut')}"
          f"  (estimate {lo:.1f}-{hi:.1f} pages)")
    print("  The official template is unpublished; confirm whether the required")
    print("  appendix counts toward the 8 pages when it lands.")
    print(f"\nwrote {out.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
