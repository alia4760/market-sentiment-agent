# Approach and roadmap

## Goal
Find which stocks are hot, and whether the conversation is bullish or bearish. Then check whether the claims behind it hold up.

## Approach
Three jobs, each with its own source:

1. **Attention: is it being talked about?** Pull the top 50 tickers from ApeWisdom (mentions and mentions 24h ago come with each one). Pick candidates two ways: the top 10 by mentions, and the top 10 by day-over-day change (ratio, with a minimum mention count so tiny jumps don't win). Take the union, up to 20 tickers. Exclude broad-market funds like SPY, QQQ and IWM, and watch for word-tickers like API and AGI. Only these candidates go on to Jev.
2. **Direction: bullish or bearish?** Jev scores the posts about each hot ticker. Roll up per ticker (share bullish vs bearish, average confidence).
3. **Confirmation: is something actually happening?** yfinance price and volume.

Top posts by upvotes skew toward gain screenshots and memes, so posts are evidence for a ticker, not the main output.

## Track record
Save each day's results so we can check them later.
- Daily snapshot per ticker: date, mentions and change, bullish/bearish share, number of posts, price on the day.
- Later, compare the price then vs now at 1 week, 1 month and 3 months, against SPY so market-wide moves don't look like wins.
- Chart how each call played out, e.g. a static page built from the saved data.
- Storage: Neon Postgres, plain SQL. Tables: `trending_snapshots`, `tradestie_snapshots`, `daily_prices`, `ticker_news`, `post_scores`, `newsletters`.
- Start saving from day one. Reddit sentiment can't be backfilled, and a 3-month check needs 3 months of data.

## Eval
- Does sentiment add anything beyond mention volume? Research on WSB suggests volume often does as well or better, so mention volume is the baseline.
- Compare Jev against a local model and a small LLM.
- Is Jev's confidence calibrated? Baseline done in `evals/` (60 finance tweets/headlines, about 83% accurate; labels under 0.5 confidence are right less than half the time). Next: hand-label 30-50 real WSB posts and rerun.

## Next
Goal: a fixed daily report, sent before the US open, that says what to look at today and why.

**Decisions made**
- **Run time:** 13:47 UTC every day (8:47am ET in winter; change to 12:47 UTC when US summer time starts in March, or it lands after the open; off the hour because GitHub delays or drops runs at :00): pre-market, before the 9:30 open. GitHub cron ignores daylight saving and can start late, so this leaves a buffer. Weekends run too, to keep weekend chatter. Could add a second run just after the open later.
- **Pre-market prices:** yfinance returns extended-hours bars (4:00am-8:00pm ET) with `prepost=True`. Tested: MU closed near $795 and traded near $776 after hours. Pre-market is thin, so treat it as a hint.
- **Roles:** facts and numbers come straight from data and fill a fixed template. Jev answers bounded questions (post sentiment, post type, headline catalyst, per-ticker bullish/bearish/mixed). One LLM call writes the short prose and is told to use only the facts it is given, so it cannot invent numbers.
- **Funnel:** wide scan of about 50 tickers with the cheap sources (ApeWisdom, Tradestie, yfinance, all batched), cut to the top 10, then spend the limited calls (Tavily, Reddit) on those only.
- **Backtest and Jev vs Tradestie wait** until there is more data (see Later).

**Build order**
1. Daily GitHub Action (written; needs repo secrets, a push, and a first manual run to check Reddit and yfinance work from GitHub's servers).
2. Word-ticker filter (done, `WORD_TICKERS` in `apewisdom.py`).
3. Pre-market price and an open-price column in `daily_prices`: prior close to latest pre-market price per ticker.
4. Earnings dates: `yfinance Ticker.calendar` gives the next date. Flag tickers reporting within a week (APP reported Nov 4, which likely explains its jump).
5. Ticker extraction: link each post to tickers it mentions (`$MU` cashtags, or uppercase words on the day's ticker list, after the word filter), then aggregate Jev labels per ticker.
6. Post-type question added to the same Jev call (analysis, news, position, meme, question); keep the useful ones. Score it on a small hand-labelled WSB sample first.
7. Tavily news for the top few tickers (test 3-4 tickers first, including whether it returns Reddit snippets), with Jev labelling each headline by catalyst: earnings, analyst, legal, product, macro.
8. Per-ticker evidence packet (attention, price, pre-market, earnings, news, post sentiment) scored by Jev as bullish, bearish or mixed with a confidence.
9. One LLM call for a short "what is going on" per top ticker plus a market overview (SPY, QQQ pre-market). Save it in `newsletters`.
10. Ticker label: news-driven, chatter ahead of price, or already moved.
11. Email the report; `sent_at` in `newsletters` stops double sends.

**Report template (per ticker)**
```
MU - news-driven | mentions 108 (was 59) | Tradestie bearish -0.03
Price: yesterday -7.0%, pre-market -2.4% | Earnings: Dec 23
Jev: bearish (0.71) | Why: <2 sentences>
```

**Known gaps**
- Only 10 posts a day, so most tickers will have 0-1 posts. Searching Reddit per ticker (or Arctic Shift) would help, but Reddit rate-limits and may block GitHub's IPs. Test first.
- Word filter loses a few real tickers (ON, DTE, IT). Edit the list if needed.
- Secrets needed by the Action: `DATABASE_URL`, `JEV_API_KEY`. Add `TAVILY_API_KEY` and an LLM key when those steps are built.

## Ideas
- More subreddits through ApeWisdom (r/stocks, r/investing, r/options).
- StockTwits: trending list plus its self-tagged bull/bear labels as a cross-check.
- Google Trends or Wikipedia pageviews as a cheap attention baseline.
- News per ticker (Tavily), to explain why it's hot. Run it only for the few hottest tickers each day, to stay inside the free tier.
- LangSmith tracing for the graph runs (free Developer plan: 5,000 traces a month, 14-day retention, so screenshot anything worth keeping). Add after the daily run is working.
- Biggest market movers from yfinance, as a label (hot and already moving vs hot but not yet) and to test whether Reddit leads or lags price. Save the daily movers list too.
- Maybe, low priority: save eval runs. Either LangSmith (its experiments feature may fit eval runs better than Postgres) or a small Postgres table. The CSVs in git are enough for now.
- Dashboard of prediction accuracy over time, and alerts when a ticker crosses a threshold.

## Later
- Backtest: does attention or sentiment lead price? Needs more days of data than the 3 weeks we have.
- Jev versus Tradestie: which one lines up better with later price moves. Decides whether Jev's sentiment step earns its place.

## Later: earnings calls
Use earnings-call transcripts as a validity check. If Reddit says a ticker is bullish, did management's tone and guidance on the last call support it, and did the stock follow? Research suggests transcript tone carries some return signal, but it is modest and fades quickly. Free transcript APIs vary, so check coverage and limits first. Treat this as a research question; a weak result is still worth writing up.
