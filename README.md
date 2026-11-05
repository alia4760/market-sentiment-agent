# market-sentiment-agent
LangGraph agent that finds which stocks are being talked about on Reddit and whether the talk is bullish or bearish.

## How it works
A LangGraph pipeline: `load_stored` checks Neon for today's newsletter and stops there if it exists. Otherwise `fetch` pulls the day's top r/wallstreetbets posts (RSS, with post body) and the trending-ticker list (ApeWisdom), `score` classifies each post as bullish, bearish or neutral with the Jev decision model (`jev.py`), `summarize` renders a plain-text newsletter, and `save` writes the trending tickers, post scores and newsletter to Neon.

The goal is ticker-first: rank tickers by how much their mentions are rising, then use post sentiment as supporting evidence. See [ROADMAP.md](ROADMAP.md) for the approach and what's next, and [evals/](evals/README.md) for the Jev baseline eval.

## Run it
Copy `.env.template.md` to `.env` and fill in your keys, then:

```
uv run main.py             # reuses today's stored newsletter if there is one
uv run main.py --refresh   # rebuild it
```

A stage that fails is recorded and the newsletter still prints, but the run exits non-zero so a scheduled job shows as failed: 2 = Reddit, 3 = ApeWisdom, 4 = Jev, 5 = database. Only a clean run stores the newsletter.

## What it stores
Postgres tables in Neon, created on first use (`storage.py`). A rerun on the same day replaces that day's rows.
- `trending_snapshots`: the day's top 50 tickers with mentions, mentions 24h ago, rank, and which were picked as candidates.
- `post_scores`: each top post with its body, Jev label and confidence.
- `newsletters`: the finished newsletter per day, with a `sent_at` column for a future email step.

## Status
Tickers and posts are not linked yet: the newsletter lists trending tickers and post sentiment separately. Per-ticker sentiment is the next step; no LLM writes the newsletter, it is a template.

## Neon (database and storage)
The Neon config lives in `neon_database/` (`neon.ts` declares the services). Run Neon CLI commands from inside that folder. To refresh the Neon variables in the root `.env`:

```
cd neon_database
neon env pull --file ../.env
```

Only run `neon deploy` after changing `neon.ts`.
