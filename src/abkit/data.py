"""Locate the dataset and query it with DuckDB."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"

REAL_PARQUET = DATA_DIR / "criteo-uplift-v2.1.parquet"
SYNTHETIC_PARQUET = DATA_DIR / "criteo-synthetic.parquet"

FEATURES = [f"f{i}" for i in range(12)]
COLUMNS = FEATURES + ["treatment", "conversion", "visit", "exposure"]


def default_data_path() -> Path:
    """Return the dataset to use: $ABKIT_DATA, else the real file, else the synthetic one."""
    if env := os.environ.get("ABKIT_DATA"):
        return Path(env)
    if REAL_PARQUET.exists():
        return REAL_PARQUET
    if SYNTHETIC_PARQUET.exists():
        return SYNTHETIC_PARQUET
    raise FileNotFoundError(
        "No dataset found. Run scripts/download_criteo.py (real data) "
        "or scripts/make_synthetic.py (fake data). See data/README.md."
    )


def is_synthetic(path: Path) -> bool:
    return Path(path).resolve() == SYNTHETIC_PARQUET.resolve()


def connect(path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with a `criteo` view over the Parquet file."""
    path = Path(path) if path else default_data_path()
    con = duckdb.connect()
    con.execute(f"CREATE VIEW criteo AS SELECT * FROM read_parquet('{path.as_posix()}')")
    return con


def run_sql_file(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    """Run a query from the sql/ folder (e.g. '01_row_counts.sql') and return a DataFrame."""
    query = (SQL_DIR / name).read_text()
    return con.execute(query).df()
