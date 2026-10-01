# AB-Test: A/B testing and uplift modeling on Criteo ad data

Did an online ad campaign actually cause more purchases, can we trust the
experiment, and *who* did the ad change? This project answers those questions
on the [Criteo Uplift dataset](data/README.md) (~14M users from a randomized ad
experiment), and packages the methods as a reusable Python library, `abkit`.

> **Status:** Steps 0–1 (setup and data exploration) are done. The results so far
> come from a **synthetic stand-in** dataset because the real download is pending.
> See [data/README.md](data/README.md).

## Quick start

```bash
pip install -e ".[dev]"
python scripts/download_criteo.py    # real data (~300 MB download), or:
python scripts/make_synthetic.py     # fake stand-in with the same columns
pytest
jupyter notebook notebooks/01_eda.ipynb
```

## Layout

```
data/README.md        where the data comes from (citation, license, columns)
scripts/              download the real data / generate fake data
sql/                  DuckDB queries for data exploration (table name: criteo)
notebooks/            analysis notebooks, one per step
src/abkit/            reusable library code
tests/                pytest suite
reports/              decision memo (later)
```

## Roadmap

| Step | Question | Status |
|---|---|---|
| 0 | Are the tools and data ready? | done (synthetic data until the real file is downloaded) |
| 1 | What does the data look like? | done: `sql/01–04`, `notebooks/01_eda.ipynb` |
| 2 | Can we trust this test? (SRM, balance, exposure) | |
| 3 | Did the ad work? (lift, CIs, power, multiple testing) | |
| 4 | Can we make the answer sharper? (regression adjustment / CUPAC) | |
| 5 | Who did the ad change? (ITT vs. IV, uplift models, Qini) | |
| 6 | Reusable package and tests | |
| 7 | Decision memo | |

## Data credit

Diemert, Betlei, Renaudin, Amini. "A Large Scale Benchmark for Uplift Modeling."
AdKDD & TargetAd Workshop, KDD 2018. Licensed CC BY-NC-SA 4.0.
