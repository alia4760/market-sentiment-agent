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
- Storage: undecided, SQLite or Neon (free hosted Postgres). Use plain SQL so either works. Decide when we get here.
- Start saving from day one. Reddit sentiment can't be backfilled, and a 3-month check needs 3 months of data.

## Eval
- Does sentiment add anything beyond mention volume? Research on WSB suggests volume often does as well or better, so mention volume is the baseline.
- Compare Jev against a local model and a small LLM.
- Is Jev's confidence calibrated? Start by hand-labelling about 20 titles.

## Next
- Pull the top 50 from ApeWisdom (currently capped at 10) and build the candidate list: top 10 by mentions plus top 10 by change.
- Ticker extraction: link each post to the tickers it discusses.
- Ticker-first scoring: gather posts per hot ticker and aggregate sentiment per ticker.
- Filter noise: separate real analysis from brags, memes and news.
- Cache fetches and fail loudly on empty results (Reddit rate-limits the RSS feed).
- yfinance price and volume as confirmation, and as the eval target.

## Ideas
- More subreddits through ApeWisdom (r/stocks, r/investing, r/options).
- StockTwits: trending list plus its self-tagged bull/bear labels as a cross-check.
- Google Trends or Wikipedia pageviews as a cheap attention baseline.
- News per ticker (Tavily), to explain why it's hot. Run it only for the few hottest tickers each day, to stay inside the free tier.
- Earnings calendar, since it explains most spikes.
- Dashboard of prediction accuracy over time, and alerts when a ticker crosses a threshold.

## Later: earnings calls
Use earnings-call transcripts as a validity check. If Reddit says a ticker is bullish, did management's tone and guidance on the last call support it, and did the stock follow? Research suggests transcript tone carries some return signal, but it is modest and fades quickly. Free transcript APIs vary, so check coverage and limits first. Treat this as a research question; a weak result is still worth writing up.
