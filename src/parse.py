"""Extract the "Item 1A. Risk Factors" section from 10-K HTML as clean text.

10-K HTML is messy: the table of contents also says "Item 1A. Risk Factors", other
sections refer to it in passing ("see Item 1A"), headings are often split across table
cells, and inline-XBRL filings carry a hidden block of tagged data. The approach:

1. HTML -> plain text with one line per block element; drop hidden XBRL and scripts.
2. Find every heading line that starts the section ("Item 1A. Risk Factors", or a bare
   "Risk Factors" line) and every heading line that starts the next one (Item 1B / 1C / 2,
   or "Unresolved Staff Comments").
3. Pair each start with the next end and keep the LONGEST span. The table of contents
   produces a short span; the real section is by far the longest.

Run:  python -m src.parse   (reads data/raw/manifest.json, writes data/sections/)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from src.config import ROOT

RAW_DIR = ROOT / "data" / "raw"
SECTIONS_DIR = ROOT / "data" / "sections"

# Sanity limits for a Risk Factors section, in words.
MIN_WORDS = 1500
MAX_WORDS = 80000

BLOCK_TAGS = [
    "p", "div", "br", "tr", "li", "table", "section",
    "h1", "h2", "h3", "h4", "h5", "h6",
]  # fmt: skip

_DASHES = "\\.:\\-–—"
START_RE = re.compile(
    rf"^[ \t]*(?:item[ \t]*1a[ \t]*[{_DASHES}]?\s*)?risk[ \t]+factors[ \t]*[.:]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
END_RE = re.compile(
    rf"^[ \t]*(?:item[ \t]*(?:1b|1c|2)\b[ \t]*[{_DASHES}]?.*"
    r"|unresolved[ \t]+staff[ \t]+comments[ \t]*[.:]?[ \t]*)$",
    re.IGNORECASE | re.MULTILINE,
)
# Lines that are page furniture, not content.
NOISE_RE = re.compile(r"^(?:\d{1,3}|page \d{1,3}|table of contents)$", re.IGNORECASE)


class ParseError(RuntimeError):
    pass


def html_to_text(html: str | bytes) -> str:
    """Plain text with one line per block element and normalized whitespace."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "ix:header"]):
        tag.decompose()
    for tag in soup.select('[style*="display:none"], [style*="display: none"]'):
        tag.decompose()
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_after("\n")
    text = soup.get_text()
    text = text.replace("\xa0", " ").replace("​", "")
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def find_risk_factors(text: str) -> str:
    """Return the body of the Risk Factors section (heading excluded)."""
    ends = [m.start() for m in END_RE.finditer(text)]
    best: tuple[int, int] | None = None
    for start in START_RE.finditer(text):
        end = next((e for e in ends if e > start.end()), None)
        if end is None:
            continue
        if best is None or end - start.end() > best[1] - best[0]:
            best = (start.end(), end)
    if best is None:
        raise ParseError("Could not find an 'Item 1A. Risk Factors' section.")
    lines = text[best[0] : best[1]].strip().split("\n")
    return "\n".join(line for line in lines if not NOISE_RE.match(line))


def extract_risk_factors(html: str | bytes) -> str:
    return find_risk_factors(html_to_text(html))


def parse_all(raw_dir: Path = RAW_DIR, out_dir: Path = SECTIONS_DIR) -> list[dict]:
    """Extract the section for every filing in the manifest. Returns per-company stats."""
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    stats, problems = [], []
    for filing in manifest:
        ticker = filing["ticker"]
        try:
            section = extract_risk_factors((ROOT / filing["path"]).read_bytes())
        except ParseError as exc:
            problems.append(f"{ticker}: {exc}")
            continue
        words = section.split()
        (out_dir / f"{ticker}.txt").write_text(section + "\n")
        stats.append(
            {
                "ticker": ticker,
                "words": len(words),
                "starts_with": " ".join(words[:12]),
                "ends_with": " ".join(words[-12:]),
            }
        )
        if not MIN_WORDS <= len(words) <= MAX_WORDS:
            problems.append(
                f"{ticker}: {len(words)} words is outside {MIN_WORDS}-{MAX_WORDS}; "
                "the wrong span was probably picked"
            )
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    if problems:
        raise ParseError("; ".join(problems))
    return stats


def main() -> None:
    try:
        stats = parse_all()
    except ParseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        stats_file = SECTIONS_DIR / "stats.json"
        if stats_file.exists():
            print(stats_file.read_text(), file=sys.stderr)
        sys.exit(1)
    for s in stats:
        print(f"{s['ticker']:5} {s['words']:6} words | {s['starts_with']} ... {s['ends_with']}")


if __name__ == "__main__":
    main()
