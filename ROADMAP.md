# Roadmap

What is built is described in the [README](README.md). This file only holds what is still to do.

## Next
- **Watch the first scheduled runs.** Unverified from GitHub's servers: Arctic Shift (it times out often, so Tavily is the backup), yfinance pre-market, the OpenAI call. Also check that the three parallel branches don't hit Jev or Tavily rate limits (both are called from more than one branch at once).
- **Run time.** GitHub cron has been 5-9 hours late on this repo, so the brief may land after the open. Options: an outside scheduler that triggers the workflow on time, or a run on the Mac.
- **Tune the system prompt** (`agent/prompts.py`) after reading a week of briefs: stance quality, length, how it handles thin evidence.
- **Record the Jev model version** per run (`brief_picks` already keeps the LLM model, prompt hash and facts).
- **Jev on comments.** The sentiment question says "post"; comments are scored with the same wording.
- **Flag degraded runs.** Fallbacks (Arctic Shift failed, PDF sent as text) only reach the log. Mention them in the report, and alert when no report was posted by a given time (GitHub sometimes drops scheduled runs).
- **Pin GitHub Actions with Dependabot** so the pinned commits get updated.

## Evaluation
Three layers, each answering a different question.

1. **Ticker matching: does it find the right posts?** A small labeled set of real Reddit snippets, each marked "about this ticker or not". Score precision and recall on every change to `mentions_ticker`. Start from the cases in `tests/test_ticker_matching.py` and add real misses.
2. **Jev: is the label right?** Baseline done in `evals/` (60 finance tweets and headlines, about 83% accurate; labels under 0.5 confidence are right less than half the time). Next: hand-label 30-50 real WSB posts and rerun. Also compare Jev with a local model and a small LLM.
3. **Picks: are they any good?** Each day's picks are stored in `brief_picks`. Later, record the price move and score each pick against its own stated horizon (day trade, swing).
   - Hit rate: share of longs that went up and shorts that went down.
   - Average return against SPY over the same window, so market-wide moves don't count as wins.
   - Results split by evidence level: do picks with more posts do better than thin ones?
   - Baseline: does sentiment add anything beyond raw mention volume? Research on WSB suggests volume often does as well or better.
   - Under about 100 picks the result is mostly noise, so this needs weeks of data. Judge all picks, not only the ones that worked.
   - Storage: picks are already saved daily in `brief_picks` (stance, horizon, top-pick rank, price at report time). Still to build: a scoring script that adds the later price moves; results as CSV in `evals/` or a small chart.

## Track record
- Compare the price at report time with 1 week, 1 month and 3 months later, against SPY.
- Chart how each call played out, e.g. a static page built from the saved data.
- Reddit sentiment can't be backfilled, and a 3-month check needs 3 months of data.

## Ideas
- More subreddits through ApeWisdom (r/stocks, r/investing, r/options).
- StockTwits: trending list plus its self-tagged bull/bear labels as a cross-check.
- Google Trends or Wikipedia pageviews as a cheap attention baseline.
- LangSmith tracing for the graph runs (free Developer plan: 5,000 traces a month, 14-day retention).
- Biggest market movers from yfinance, as a label (hot and already moving vs hot but not yet) and to test whether Reddit leads or lags price.
- Save eval runs, either in LangSmith experiments or a small Postgres table. The CSVs in git are enough for now.
- Dashboard of prediction accuracy over time, and alerts when a ticker crosses a threshold.
- Cost watch: each run uses about 100 Jev calls, 10-20 Tavily credits and one LLM call.

## Later
- Backtest: does attention or sentiment lead price? Needs more days of data than we have.
- Jev versus Tradestie: which one lines up better with later price moves. Decides whether Jev's sentiment step earns its place.
- **Earnings calls as a validity check.** If Reddit says a ticker is bullish, did management's tone and guidance on the last call support it, and did the stock follow? Transcript tone carries a modest return signal that fades quickly. Free transcript APIs vary, so check coverage and limits first. A weak result is still worth writing up.
