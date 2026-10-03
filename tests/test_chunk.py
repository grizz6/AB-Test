import json

import pytest

from src import chunk


def words(n):
    return " ".join(f"w{i}" for i in range(n))


def test_windows_have_size_and_overlap():
    windows = chunk.split_words(words(1000), size=400, overlap=50)
    assert [len(w.split()) for w in windows] == [400, 400, 300]
    first, second = windows[0].split(), windows[1].split()
    assert first[-50:] == second[:50]  # 50-word overlap


def test_every_word_is_covered_once_overlap_removed():
    text = words(1234)
    windows = chunk.split_words(text, size=400, overlap=50)
    rebuilt = windows[0].split()
    for w in windows[1:]:
        rebuilt += w.split()[50:]
    assert rebuilt == text.split()


@pytest.mark.parametrize("n", [1, 399, 400])
def test_short_text_is_one_chunk(n):
    assert len(chunk.split_words(words(n), size=400, overlap=50)) == 1


def test_no_tiny_trailing_chunk_made_only_of_overlap():
    # 750 words: windows start at 0 and 350; the second reaches the end, so no third.
    assert len(chunk.split_words(words(750), size=400, overlap=50)) == 2


def test_empty_text_and_bad_settings():
    assert chunk.split_words("   ", 400, 50) == []
    with pytest.raises(ValueError):
        chunk.split_words("a b", 400, 400)


def test_chunk_ids_unique_and_formatted():
    filing = {"ticker": "TSLA", "company": "Tesla", "url": "u", "filing_date": "2026-01-29"}
    chunks = chunk.chunk_filing(words(5000), filing, size=400, overlap=50)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
    assert ids[0] == "TSLA_1A_0000" and ids[12] == "TSLA_1A_0012"
    assert all(c["text"] and c["source_url"] == "u" for c in chunks)


def test_chunk_all_writes_jsonl(tmp_path):
    raw, sections = tmp_path / "raw", tmp_path / "sections"
    raw.mkdir()
    sections.mkdir()
    manifest = [
        {"ticker": t, "company": t, "url": f"https://x/{t}", "filing_date": "2026-01-01"}
        for t in ("AAPL", "TSLA")
    ]
    (raw / "manifest.json").write_text(json.dumps(manifest))
    for t in ("AAPL", "TSLA"):
        (sections / f"{t}.txt").write_text(words(900))
    out = tmp_path / "chunks.jsonl"

    chunks = chunk.chunk_all(400, 50, raw_dir=raw, sections_dir=sections, out_path=out)

    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert lines == chunks
    assert len({c["id"] for c in chunks}) == len(chunks) == 6  # 3 per company
