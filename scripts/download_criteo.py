"""Download the Criteo Uplift v2.1 CSV and convert it to data/criteo-uplift-v2.1.parquet.

Usage:
    python scripts/download_criteo.py                 # download, then convert
    python scripts/download_criteo.py --csv FILE      # convert a CSV(.gz) you already have
"""

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from abkit.data import COLUMNS, DATA_DIR, REAL_PARQUET  # noqa: E402

URLS = [
    "http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz",
    "https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz",
]
EXPECTED_ROWS = 13_979_592


def download(dest: Path) -> Path:
    for url in URLS:
        try:
            print(f"Downloading {url} ...")
            with urllib.request.urlopen(url) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out, length=1 << 20)
            return dest
        except Exception as exc:  # try the next mirror
            print(f"  failed: {exc}")
    sys.exit("All download URLs failed. Download the file manually and pass --csv.")


def convert(csv_path: Path, out: Path) -> None:
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT {", ".join(COLUMNS)} FROM read_csv_auto('{csv_path.as_posix()}'))
        TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out.as_posix()}')").fetchone()[0]
    print(f"Wrote {n:,} rows to {out}")
    if n != EXPECTED_ROWS:
        print(f"WARNING: expected {EXPECTED_ROWS:,} rows; check the source file.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Existing CSV or CSV.gz to convert")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    csv_path = args.csv or download(DATA_DIR / "criteo-research-uplift-v2.1.csv.gz")
    convert(csv_path, REAL_PARQUET)


if __name__ == "__main__":
    main()
