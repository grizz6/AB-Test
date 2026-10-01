"""Download the latest 10-K filing (HTML) for each company in config.yaml from SEC EDGAR.

SEC rules followed here:
* Every request sends a User-Agent of the form "Name email", read from the
  SEC_USER_AGENT environment variable (a repo secret in CI, .env locally).
* At most 10 requests per second: requests are spaced at least 0.2 s apart.

Output: data/raw/<TICKER>_10-K_<filing date>.htm plus data/raw/manifest.json, which
records where each file came from (needed for citations later).

Run:  python -m src.download
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from src.config import ROOT, load_config

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

RAW_DIR = ROOT / "data" / "raw"
MIN_INTERVAL_SECONDS = 0.2
MAX_RETRIES = 4
TIMEOUT_SECONDS = 60


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Filing:
    ticker: str
    company: str
    cik: str  # 10 digits, zero-padded
    form: str
    accession: str
    filing_date: str
    report_date: str
    primary_document: str
    url: str
    path: str = ""


def pad_cik(cik: int | str) -> str:
    """SEC wants 10-digit CIKs with leading zeros: 320193 -> '0000320193'."""
    return f"{int(cik):010d}"


def user_agent() -> str:
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua or "@" not in ua:
        raise DownloadError('SEC_USER_AGENT must be set to "Your Name your.email@example.com".')
    return ua


class SecClient:
    """HTTP client that sends the SEC User-Agent, spaces requests out, and retries."""

    def __init__(self, ua: str, session: requests.Session | None = None, sleep=time.sleep):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
        self._sleep = sleep
        self._last_request = 0.0

    def _throttle(self) -> None:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_request)
        if wait > 0:
            self._sleep(wait)
        self._last_request = time.monotonic()

    def get(self, url: str) -> requests.Response:
        for attempt in range(MAX_RETRIES + 1):
            self._throttle()
            resp = self.session.get(url, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                self._sleep(2**attempt)  # back off: 1, 2, 4, 8 s
                continue
            raise DownloadError(f"GET {url} -> {resp.status_code}: {resp.text[:200]}")
        raise AssertionError("unreachable")


def cik_lookup(client: SecClient) -> dict[str, str]:
    """Map ticker -> 10-digit CIK using SEC's public ticker file."""
    data = client.get(TICKERS_URL).json()
    return {row["ticker"].upper(): pad_cik(row["cik_str"]) for row in data.values()}


def latest_10k(submissions: dict, ticker: str, company: str, cik: str) -> Filing:
    """Pick the most recent original 10-K (not an amendment) from a submissions JSON."""
    recent = submissions["filings"]["recent"]
    for i, form in enumerate(recent["form"]):
        if form == "10-K":
            accession = recent["accessionNumber"][i]
            document = recent["primaryDocument"][i]
            url = ARCHIVE_URL.format(
                cik=int(cik), accession=accession.replace("-", ""), document=document
            )
            return Filing(
                ticker=ticker,
                company=company,
                cik=cik,
                form=form,
                accession=accession,
                filing_date=recent["filingDate"][i],
                report_date=recent["reportDate"][i],
                primary_document=document,
                url=url,
            )
    raise DownloadError(f"No 10-K found in recent filings for {ticker} (CIK {cik}).")


def download_all(companies: dict[str, str], client: SecClient, out_dir: Path = RAW_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    ciks = cik_lookup(client)
    filings = []
    for ticker, company in companies.items():
        cik = ciks.get(ticker.upper())
        if cik is None:
            raise DownloadError(f"Ticker {ticker} not found in SEC ticker list.")
        filing = latest_10k(
            client.get(SUBMISSIONS_URL.format(cik=cik)).json(), ticker, company, cik
        )
        html = client.get(filing.url).content
        path = out_dir / f"{ticker}_10-K_{filing.filing_date}.htm"
        path.write_bytes(html)
        filing = Filing(**{**asdict(filing), "path": str(path.relative_to(ROOT))})
        filings.append(filing)
        print(f"{ticker:5} {filing.filing_date}  {len(html) / 1e6:5.1f} MB  {filing.url}")
    manifest = out_dir / "manifest.json"
    manifest.write_text(json.dumps([asdict(f) for f in filings], indent=2) + "\n")
    return filings


def main() -> None:
    try:
        client = SecClient(user_agent())
        filings = download_all(load_config()["companies"], client)
    except DownloadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Downloaded {len(filings)} filings to {RAW_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
