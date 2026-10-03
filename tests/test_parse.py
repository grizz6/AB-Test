import json

import pytest

from src import parse

RISK_BODY = " ".join(["Our supply chain depends on a limited number of suppliers."] * 30)

# Shaped like a real inline-XBRL 10-K: hidden XBRL header, a table of contents that also
# says "Item 1A. Risk Factors", a cross-reference in Item 1, a heading split across two
# table cells, page numbers, then Item 1B.
FILING = f"""
<html><head><title>10-K</title><style>.x{{color:red}}</style></head><body>
<div style="display:none"><ix:header>Item 1A. Risk Factors hidden xbrl data</ix:header></div>
<table>
  <tr><td>Item 1.</td><td>Business</td><td>3</td></tr>
  <tr><td><a href="#rf">Item 1A.</a></td><td>Risk Factors</td><td>12</td></tr>
  <tr><td>Item 1B.</td><td>Unresolved Staff Comments</td><td>30</td></tr>
  <tr><td>Item 2.</td><td>Properties</td><td>31</td></tr>
</table>
<div><span>Item&#160;1.</span> <span>Business</span></div>
<p>We make cars. For more, see Item 1A. Risk Factors below.</p>
<table><tr><td><span style="font-weight:bold">Item 1A.</span></td></tr>
<tr><td><span style="font-weight:bold">Risk&#160;Factors</span></td></tr></table>
<p>{RISK_BODY}</p>
<p>12</p>
<p>Table of Contents</p>
<p>Competition in our industry is <b>intense</b>.</p>
<div><span>Item 1B.</span> <span>Unresolved Staff Comments</span></div>
<p>None.</p>
<div>Item 2. Properties</div>
<p>We own factories.</p>
</body></html>
"""


def test_html_to_text_drops_hidden_xbrl_and_scripts():
    text = parse.html_to_text(FILING)
    assert "hidden xbrl data" not in text
    assert "color:red" not in text
    assert "Item 1. Business" in text  # inline spans stay on one line, nbsp normalized


def test_extracts_real_section_not_table_of_contents():
    section = parse.extract_risk_factors(FILING)
    assert section.startswith("Our supply chain depends")
    assert section.endswith("Competition in our industry is intense.")
    assert "Unresolved Staff Comments" not in section
    assert "We make cars" not in section  # cross-reference in Item 1 is not a heading


def test_page_numbers_and_running_headers_removed():
    section = parse.extract_risk_factors(FILING)
    lines = section.split("\n")
    assert "12" not in lines
    assert "Table of Contents" not in lines


def test_bare_risk_factors_heading_and_item_1c_end():
    html = f"""<html><body>
    <p>Risk Factors</p><p>Item 1C. Cybersecurity</p>
    <h2>RISK FACTORS</h2><p>{RISK_BODY}</p>
    <h2>Item 1C. Cybersecurity</h2><p>We have a security program.</p>
    </body></html>"""
    section = parse.extract_risk_factors(html)
    assert section.startswith("Our supply chain")
    assert "security program" not in section


def test_missing_section_raises():
    with pytest.raises(parse.ParseError, match="Risk Factors"):
        parse.extract_risk_factors("<html><body><p>Item 1. Business</p></body></html>")


def _write_filing(tmp_path, monkeypatch, html, ticker="TSLA"):
    monkeypatch.setattr(parse, "ROOT", tmp_path)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / f"{ticker}.htm").write_text(html)
    manifest = [{"ticker": ticker, "path": f"data/raw/{ticker}.htm"}]
    (raw / "manifest.json").write_text(json.dumps(manifest))
    return raw, tmp_path / "data" / "sections"


def test_parse_all_writes_sections_and_stats(tmp_path, monkeypatch):
    long_body = " ".join(["Risk word"] * 1000)  # 2000 words, inside the sanity range
    html = f"<p>Item 1A. Risk Factors</p><p>{long_body}</p><p>Item 2. Properties</p>"
    raw, out = _write_filing(tmp_path, monkeypatch, html)
    stats = parse.parse_all(raw, out)
    assert stats[0]["ticker"] == "TSLA" and stats[0]["words"] == 2000
    assert (out / "TSLA.txt").read_text().startswith("Risk word")
    assert json.loads((out / "stats.json").read_text())[0]["words"] == 2000


def test_parse_all_flags_suspiciously_short_section(tmp_path, monkeypatch):
    html = "<p>Item 1A. Risk Factors</p><p>Too short.</p><p>Item 2. Properties</p>"
    raw, out = _write_filing(tmp_path, monkeypatch, html)
    with pytest.raises(parse.ParseError, match="TSLA: 2 words"):
        parse.parse_all(raw, out)
