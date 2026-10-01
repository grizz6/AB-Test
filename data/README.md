# Data

Nothing in this folder is committed except this file. Rebuild the data with the
scripts below.

## Source: Criteo Uplift Prediction Dataset (v2.1)

- **Made by:** Criteo AI Lab
- **What it is:** about 14 million users from a randomized online-advertising
  experiment. Each row is one user.
- **Official page:** https://ailab.criteo.com/criteo-uplift-prediction-dataset/
- **Download:** http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz
  (mirror: https://huggingface.co/datasets/criteo/criteo-uplift)
- **License:** CC BY-NC-SA 4.0. Non-commercial use only, give attribution,
  and share derived data under the same license.

### Citation

> Eustache Diemert, Artem Betlei, Christophe Renaudin, and Massih-Reza Amini.
> "A Large Scale Benchmark for Uplift Modeling." *AdKDD & TargetAd Workshop,
> KDD 2018*, London, United Kingdom.

```bibtex
@inproceedings{Diemert2018,
  author    = {Diemert, Eustache and Betlei, Artem and Renaudin, Christophe and Amini, Massih-Reza},
  title     = {A Large Scale Benchmark for Uplift Modeling},
  booktitle = {Proceedings of the AdKDD and TargetAd Workshop, KDD},
  address   = {London, United Kingdom},
  year      = {2018}
}
```

### Columns

| Column | Type | Meaning |
|---|---|---|
| `f0` … `f11` | float | 12 anonymized user features, recorded before the experiment |
| `treatment` | 0/1 | 1 = put in the ad group, 0 = control (no ads) |
| `exposure` | 0/1 | 1 = actually shown an ad (can only be 1 when `treatment` = 1) |
| `visit` | 0/1 | 1 = visited the advertiser's website |
| `conversion` | 0/1 | 1 = bought something |

## Getting the real data

```bash
python scripts/download_criteo.py            # downloads ~300 MB, writes data/criteo-uplift-v2.1.parquet
python scripts/download_criteo.py --csv path/to/criteo-research-uplift-v2.1.csv.gz   # or convert a file you already have
```

## Fake stand-in data (used until the real data is available)

```bash
python scripts/make_synthetic.py             # writes data/criteo-synthetic.parquet (2M rows)
```

This file is **made up**. It has the same columns as the real data, and its
rates are set to roughly match the published ones (85/15 split, ~3% exposure in
treatment, ~4.7% visits, ~0.3% conversions). The ad effect, and the fact that
people who saw the ad differ from those who didn't, are built in on purpose.
Do not report any number from it as a finding.

`abkit.data.default_data_path()` uses the real Parquet file when it exists and
falls back to the fake one otherwise. Every notebook prints which one it used.
