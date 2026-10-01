import pandas as pd
import pytest

from abkit.data import COLUMNS, SQL_DIR, connect, run_sql_file
from abkit.synthetic import generate


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "fake.parquet"
    generate(n_rows=200_000, seed=0).to_parquet(path, index=False)
    return connect(path)


def test_synthetic_has_criteo_schema():
    df = generate(n_rows=10_000, seed=1)
    assert list(df.columns) == COLUMNS


def test_synthetic_respects_dataset_rules(con):
    rows = run_sql_file(con, "01_row_counts.sql").iloc[0]
    assert rows.n_rows == 200_000
    assert rows.exposed_but_control == 0
    assert rows.converted_without_visit == 0


def test_synthetic_rates_near_targets(con):
    groups = run_sql_file(con, "03_group_sizes.sql").set_index("grp")
    assert groups.loc["treatment", "share_of_users"] == pytest.approx(0.85, abs=0.005)

    rates = run_sql_file(con, "04_rates_by_group.sql").set_index("grp")
    assert rates.loc["control", "visit_rate"] == pytest.approx(0.038, abs=0.003)
    assert rates.loc["treatment", "visit_rate"] == pytest.approx(0.0485, abs=0.002)
    assert rates.loc["treatment", "exposure_rate"] == pytest.approx(0.036, abs=0.002)
    assert rates.loc["control", "exposure_rate"] == 0


@pytest.mark.parametrize("sql_file", sorted(p.name for p in SQL_DIR.glob("*.sql")))
def test_every_sql_file_runs(con, sql_file):
    assert isinstance(run_sql_file(con, sql_file), pd.DataFrame)
