"""Sample a small balanced eval set from zeroshot/twitter-financial-news-sentiment.

Usage: uv run evals/build_eval_set.py [--per-label 15] [--seed 42]
"""
import argparse
import csv
import random
from pathlib import Path

import requests

DATASET = "zeroshot/twitter-financial-news-sentiment"
SPLIT = "validation"
LABELS = {0: "bearish", 1: "bullish", 2: "neutral"}  # from the dataset card
OUT = Path(__file__).parent / "eval_set.csv"


def fetch_rows() -> list[dict]:
    rows, offset = [], 0
    while True:
        resp = requests.get(
            "https://datasets-server.huggingface.co/rows",
            params={"dataset": DATASET, "config": "default", "split": SPLIT,
                    "offset": offset, "length": 100},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()["rows"]
        if not batch:
            return rows
        rows.extend(r["row"] | {"row_idx": r["row_idx"]} for r in batch)
        offset += len(batch)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-label", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = fetch_rows()
    rng = random.Random(args.seed)
    sample = []
    for label_id, label in LABELS.items():
        pool = [r for r in rows if r["label"] == label_id]
        sample += [(r, label) for r in rng.sample(pool, args.per_label)]
    rng.shuffle(sample)

    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "text", "label", "source"])
        for i, (r, label) in enumerate(sample, 1):
            writer.writerow([i, r["text"], label, f"{DATASET}/{SPLIT}#{r['row_idx']}"])
    print(f"Wrote {len(sample)} rows to {OUT} (from {len(rows)} in {SPLIT})")


if __name__ == "__main__":
    main()
