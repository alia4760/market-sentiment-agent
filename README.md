# market-sentiment-agent
LangGraph agent that finds which stocks are being talked about on Reddit and whether the talk is bullish or bearish.

## How it works
A fixed three-node LangGraph pipeline: `fetch` pulls the day's top r/wallstreetbets posts (RSS, with post body) and the trending-ticker list (ApeWisdom), `score` classifies each post as bullish, bearish or neutral with the Jev decision model, and `summarize` renders the result into a plain-text newsletter.

The goal is ticker-first: rank tickers by how much their mentions are rising, then use post sentiment as supporting evidence. See [ROADMAP.md](ROADMAP.md) for the approach and what's next.

## Run it
Copy `.env.template.md` to `.env` and add your `JEV_API_KEY`, then:

```
uv run main.py
```

## Neon (database and storage)
The Neon config lives in `neon_database/` (`neon.ts` declares the services). Run Neon CLI commands from inside that folder. To refresh the Neon variables in the root `.env`:

```
cd neon_database
neon env pull --file ../.env
```

Only run `neon deploy` after changing `neon.ts`.
