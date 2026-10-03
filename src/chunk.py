"""Split each Risk Factors section into overlapping word windows.

Each chunk gets a stable ID like TSLA_1A_0012 and carries the metadata needed for
citations (company, source URL, filing date).

Run:  python -m src.chunk   (reads data/sections/ + data/raw/manifest.json,
                             writes data/chunks.jsonl)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.config import ROOT, load_config

RAW_DIR = ROOT / "data" / "raw"
SECTIONS_DIR = ROOT / "data" / "sections"
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"


def split_words(text: str, size: int, overlap: int) -> list[str]:
    """Windows of `size` words; each starts `size - overlap` words after the previous one."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    words = text.split()
    if not words:
        return []
    step = size - overlap
    windows = []
    for start in range(0, len(words), step):
        windows.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return windows


def chunk_id(ticker: str, index: int) -> str:
    return f"{ticker}_1A_{index:04d}"


def chunk_filing(section: str, filing: dict, size: int, overlap: int) -> list[dict]:
    return [
        {
            "id": chunk_id(filing["ticker"], i),
            "ticker": filing["ticker"],
            "company": filing["company"],
            "chunk_index": i,
            "text": text,
            "n_words": len(text.split()),
            "source_url": filing["url"],
            "filing_date": filing["filing_date"],
        }
        for i, text in enumerate(split_words(section, size, overlap))
    ]


def chunk_all(
    size: int,
    overlap: int,
    raw_dir: Path = RAW_DIR,
    sections_dir: Path = SECTIONS_DIR,
    out_path: Path = CHUNKS_PATH,
) -> list[dict]:
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    chunks = []
    for filing in manifest:
        section = (sections_dir / f"{filing['ticker']}.txt").read_text()
        chunks.extend(chunk_filing(section, filing, size, overlap))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    return chunks


def main() -> None:
    cfg = load_config()["chunking"]
    chunks = chunk_all(cfg["size_words"], cfg["overlap_words"])
    per_ticker: dict[str, int] = {}
    for c in chunks:
        per_ticker[c["ticker"]] = per_ticker.get(c["ticker"], 0) + 1
    for ticker, n in per_ticker.items():
        print(f"{ticker:5} {n:4} chunks")
    print(f"Total: {len(chunks)} chunks -> {CHUNKS_PATH.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
