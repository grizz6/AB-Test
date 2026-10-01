import json

import pytest

from src import download


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    """Returns queued responses per URL and records every request."""

    def __init__(self, routes):
        self.routes = {url: list(resps) for url, resps in routes.items()}
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        return self.routes[url].pop(0)


SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": ["8-K", "10-K/A", "10-K", "10-Q", "10-K"],
            "accessionNumber": ["a-1", "0000320193-25-000080", "0000320193-24-000123", "q", "old"],
            "filingDate": ["2025-12-01", "2025-11-20", "2024-11-01", "2024-08-02", "2023-11-03"],
            "reportDate": ["", "2025-09-27", "2024-09-28", "2024-06-29", "2023-09-30"],
            "primaryDocument": ["x.htm", "amend.htm", "aapl-20240928.htm", "q.htm", "o.htm"],
        }
    }
}


def test_pad_cik():
    assert download.pad_cik(320193) == "0000320193"
    assert download.pad_cik("789019") == "0000789019"


@pytest.mark.parametrize("value", ["", "   ", "Just A Name"])
def test_user_agent_must_have_name_and_email(monkeypatch, value):
    monkeypatch.setenv("SEC_USER_AGENT", value)
    with pytest.raises(download.DownloadError, match="SEC_USER_AGENT"):
        download.user_agent()


def test_user_agent_ok(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Jane Doe jane@example.com")
    assert download.user_agent() == "Jane Doe jane@example.com"


def test_latest_10k_skips_amendments_and_builds_archive_url():
    f = download.latest_10k(SUBMISSIONS, "AAPL", "Apple", "0000320193")
    assert f.form == "10-K"
    assert f.accession == "0000320193-24-000123"
    assert f.filing_date == "2024-11-01"
    assert f.url == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
    )


def test_latest_10k_missing_raises():
    subs = {"filings": {"recent": {k: ["8-K"] for k in SUBMISSIONS["filings"]["recent"]}}}
    with pytest.raises(download.DownloadError, match="No 10-K"):
        download.latest_10k(subs, "XYZ", "Xyz", "0000000001")


def test_client_sends_user_agent_and_throttles():
    session = FakeSession({"u": [FakeResponse(), FakeResponse()]})
    sleeps = []
    client = download.SecClient("Jane jane@example.com", session=session, sleep=sleeps.append)
    client.get("u")
    client.get("u")
    assert session.headers["User-Agent"] == "Jane jane@example.com"
    # second call comes immediately after the first, so it must wait ~0.2 s
    assert len(sleeps) == 1 and 0 < sleeps[0] <= download.MIN_INTERVAL_SECONDS


def test_client_retries_rate_limit_then_succeeds():
    session = FakeSession({"u": [FakeResponse(429), FakeResponse(503), FakeResponse(200)]})
    sleeps = []
    client = download.SecClient("Jane jane@example.com", session=session, sleep=sleeps.append)
    assert client.get("u").status_code == 200
    assert len(session.calls) == 3
    assert 1 in sleeps and 2 in sleeps  # exponential backoff


def test_client_does_not_retry_client_errors():
    session = FakeSession({"u": [FakeResponse(404, text="nope")]})
    client = download.SecClient("Jane jane@example.com", session=session, sleep=lambda s: None)
    with pytest.raises(download.DownloadError, match="404"):
        client.get("u")


def test_download_all_writes_files_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "ROOT", tmp_path)
    tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
    doc_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
    session = FakeSession(
        {
            download.TICKERS_URL: [FakeResponse(payload=tickers)],
            download.SUBMISSIONS_URL.format(cik="0000320193"): [FakeResponse(payload=SUBMISSIONS)],
            doc_url: [FakeResponse(content=b"<html>Item 1A. Risk Factors</html>")],
        }
    )
    client = download.SecClient("Jane jane@example.com", session=session, sleep=lambda s: None)
    out = tmp_path / "data" / "raw"

    filings = download.download_all({"AAPL": "Apple"}, client, out_dir=out)

    html_file = out / "AAPL_10-K_2024-11-01.htm"
    assert html_file.read_bytes() == b"<html>Item 1A. Risk Factors</html>"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest[0]["ticker"] == "AAPL"
    assert manifest[0]["url"] == doc_url
    assert manifest[0]["path"] == "data/raw/AAPL_10-K_2024-11-01.htm"
    assert filings[0].cik == "0000320193"


def test_cik_override_replaces_ticker_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "ROOT", tmp_path)
    # SEC's ticker list points XOM at a new CIK with no 10-K; the override wins.
    tickers = {"0": {"cik_str": 2115436, "ticker": "XOM", "title": "ExxonMobil Holdings"}}
    subs = {
        "filings": {
            "recent": {
                "form": ["10-K"],
                "accessionNumber": ["0000034088-26-000010"],
                "filingDate": ["2026-02-18"],
                "reportDate": ["2025-12-31"],
                "primaryDocument": ["xom-20251231.htm"],
            }
        }
    }
    doc_url = "https://www.sec.gov/Archives/edgar/data/34088/000003408826000010/xom-20251231.htm"
    session = FakeSession(
        {
            download.TICKERS_URL: [FakeResponse(payload=tickers)],
            download.SUBMISSIONS_URL.format(cik="0000034088"): [FakeResponse(payload=subs)],
            doc_url: [FakeResponse(content=b"<html></html>")],
        }
    )
    client = download.SecClient("Jane jane@example.com", session=session, sleep=lambda s: None)
    filings = download.download_all(
        {"XOM": "Exxon Mobil"}, client, out_dir=tmp_path / "raw", cik_overrides={"XOM": 34088}
    )
    assert filings[0].cik == "0000034088"
    assert filings[0].url == doc_url


def test_config_overrides_are_valid():
    from src.config import load_config

    cfg = load_config()
    for ticker, cik in (cfg.get("cik_overrides") or {}).items():
        assert ticker in cfg["companies"]
        assert download.pad_cik(cik).isdigit()


def test_unknown_ticker_raises(tmp_path):
    session = FakeSession({download.TICKERS_URL: [FakeResponse(payload={})]})
    client = download.SecClient("Jane jane@example.com", session=session, sleep=lambda s: None)
    with pytest.raises(download.DownloadError, match="ZZZZ"):
        download.download_all({"ZZZZ": "Nope"}, client, out_dir=tmp_path)
