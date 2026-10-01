"""Write a fake stand-in for the Criteo data to data/criteo-synthetic.parquet."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from abkit.data import SYNTHETIC_PARQUET  # noqa: E402
from abkit.synthetic import generate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=2_000_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=SYNTHETIC_PARQUET)
    args = parser.parse_args()

    df = generate(args.rows, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df):,} fake rows to {args.out}")


if __name__ == "__main__":
    main()
