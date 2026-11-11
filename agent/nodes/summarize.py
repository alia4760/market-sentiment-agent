from agent.state import State
from sources.earnings import describe as describe_earnings


def _last_move(prices: list[dict]) -> dict[str, float]:
    """Latest day's % change in close, per ticker."""
    by_ticker: dict[str, list[dict]] = {}
    for row in prices:
        by_ticker.setdefault(row["ticker"], []).append(row)
    moves = {}
    for ticker, rows in by_ticker.items():
        rows.sort(key=lambda r: r["date"])
        if len(rows) >= 2 and rows[-2]["close"]:
            moves[ticker] = (rows[-1]["close"] / rows[-2]["close"] - 1) * 100
    return moves


def summarize(state: State) -> dict:
    lines = ["=== Market Sentiment Newsletter ===", "", "Trending tickers:"]
    tradestie = {r["ticker"]: r for r in state.get("tradestie") or []}
    moves = _last_move(state.get("prices") or [])
    if state.get("trending"):
        for stock in state["trending"]:
            picked = "+".join(stock["picked_by"])
            ticker = stock["ticker"]
            extras = []
            if tradestie.get(ticker):
                t = tradestie[ticker]
                extras.append(f"Tradestie {t['sentiment'].lower()} {t['sentiment_score']:+.2f}")
            price = []
            if ticker in moves:
                price.append(f"prev day {moves[ticker]:+.1f}%")
            pm = (state.get("premarket") or {}).get(ticker)
            if pm:
                label = {"pre": "pre-market", "post": "after-hours", "regular": "live"}[pm["session"]]
                price.append(f"{label} {pm['pct']:+.1f}%")
            if price:
                extras.append(", ".join(price))
            if ticker in (state.get("earnings") or {}):
                extras.append(f"earnings {describe_earnings(state['earnings'][ticker])}")
            mentions = stock.get("mentions")
            was = stock.get("mentions_24h_ago", "N/A")
            lines.append(
                f"  {ticker}: "
                + (f"{mentions} mentions (was {was}) " if mentions is not None else "")
                + f"[{picked}]"
                + (f"  | {' | '.join(extras)}" if extras else "")
            )
            for article in (state.get("news") or {}).get(ticker, [])[:2]:
                lines.append(f"      - {article['title']}")
    else:
        lines.append("  (unavailable today)")

    lines.append("")
    lines.append("WSB post sentiment:")
    if state.get("scores"):
        for item in state["scores"]:
            lines.append(f"  [{item['label']} ({item['confidence']:.2f})] {item['title']}")
    else:
        lines.append("  (skipped: collect-only run)" if state.get("collect_only") else "  (unavailable today)")

    return {"newsletter": "\n".join(lines)}
