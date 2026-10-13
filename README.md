# market-sentiment-agent
LangGraph multi-agent system that surfaces trending tickers from various sources.

## Architecture
A fixed three-node LangGraph pipeline: `fetch` pulls the day's top r/wallstreetbets
posts (RSS) and the current trending-ticker list (ApeWisdom), `score` labels each
post's sentiment (currently stubbed to `neutral`/`0.0` until a real model is wired
in), and `summarize` renders the trending tickers and scored posts into a plain-text
newsletter string. State flows through unchanged as `posts → scores → newsletter`.

## Run it
```
uv run main.py
```
