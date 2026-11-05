# Jev sentiment eval

Baseline check of the Jev classifier in `jev.py` (the same `SENTIMENT_QUESTION` the agent uses).

```
uv run evals/build_eval_set.py   # rebuild eval_set.csv (optional)
uv run evals/run_eval.py         # one API call per row; --limit N for a quick check
```

Prints accuracy, per-label precision/recall, a confusion table and a confidence calibration table. Per-row results go to `results.csv`.

## Data
- **Source:** [zeroshot/twitter-financial-news-sentiment](https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment), `validation` split (2,388 rows fetched).
- **Labels:** 0 = bearish, 1 = bullish, 2 = neutral (from the dataset card).
- **Sample:** 20 per label (60 rows), seed 42, shuffled.
- **License:** MIT (Twitter Financial News dataset, sentiment, v1.0.0). The dataset card gives no citation, so credit the Hugging Face page above.

## Caveats
- This is tweets and news headlines, **not WSB posts**. It shows whether Jev reads finance text sensibly, not how well it does on WSB slang and memes. Treat it as a baseline.
- 20 rows per label is still small: one wrong row moves a per-label number by 5 points.
- The sample is balanced by design, so accuracy here is not accuracy on real, mostly-neutral data. Look at per-label recall.
