"""Baseline eval of the Jev sentiment classifier on evals/eval_set.csv.

Usage: uv run evals/run_eval.py [--limit N]
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.jev import classify_sentiment  # noqa: E402

HERE = Path(__file__).parent
LABELS = ["bullish", "bearish", "neutral"]
BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


def classify_all(texts: list[str]) -> list[dict]:
    """Batch call; if the batch fails, retry one by one so a bad row can't sink the run."""
    try:
        return classify_sentiment(texts)
    except Exception as e:
        print(f"Batch failed ({e!r}); retrying row by row")
    results = []
    for text in texts:
        try:
            results.append(classify_sentiment([text])[0])
        except Exception as e:
            results.append({"label": None, "confidence": None, "error": repr(e)})
    return results


def report(rows: list[dict]) -> None:
    ok = [r for r in rows if r["predicted"]]
    errors = len(rows) - len(ok)
    correct = sum(r["predicted"] == r["label"] for r in ok)
    print(f"\nOverall accuracy: {correct}/{len(ok)} = {correct / len(ok):.1%}"
          + (f"  ({errors} errored rows excluded)" if errors else ""))

    print("\nPer label:")
    print(f"  {'label':<9}{'n':>4}{'precision':>11}{'recall':>9}")
    for label in LABELS:
        n = sum(r["label"] == label for r in ok)
        predicted = sum(r["predicted"] == label for r in ok)
        hit = sum(r["label"] == label == r["predicted"] for r in ok)
        precision = f"{hit / predicted:.0%}" if predicted else "n/a"
        recall = f"{hit / n:.0%}" if n else "n/a"
        print(f"  {label:<9}{n:>4}{precision:>11}{recall:>9}")

    print("\nConfusion (rows = true, columns = predicted):")
    print(f"  {'':<9}" + "".join(f"{label:>9}" for label in LABELS))
    for true in LABELS:
        counts = [sum(r["label"] == true and r["predicted"] == p for r in ok) for p in LABELS]
        print(f"  {true:<9}" + "".join(f"{c:>9}" for c in counts))

    print("\nCalibration (confidence -> how often Jev was right):")
    print(f"  {'bucket':<10}{'n':>4}{'accuracy':>10}")
    for lo, hi in BUCKETS:
        bucket = [r for r in ok if lo <= r["confidence"] < hi]
        name = f"{lo:.1f}-{min(hi, 1.0):.1f}" if hi <= 1 else f">={lo:.1f}"
        acc = f"{sum(r['predicted'] == r['label'] for r in bucket) / len(bucket):.0%}" if bucket else "n/a"
        print(f"  {name:<10}{len(bucket):>4}{acc:>10}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only use the first N rows")
    args = parser.parse_args()

    with (HERE / "eval_set.csv").open() as f:
        data = list(csv.DictReader(f))
    if args.limit:
        data = data[: args.limit]

    print(f"Sending {len(data)} texts to Jev ({len(data)} API calls)")
    results = classify_all([row["text"] for row in data])

    rows = [
        {**row, "predicted": res["label"], "confidence": res["confidence"],
         "error": res.get("error", "")}
        for row, res in zip(data, results)
    ]
    with (HERE / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "text", "label", "predicted", "confidence", "error", "source"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    report(rows)


if __name__ == "__main__":
    main()
