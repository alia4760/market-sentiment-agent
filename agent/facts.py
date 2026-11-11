"""Turn the pipeline state into one plain facts record per candidate ticker.

Both the LLM prompt and the report template read these records, so every number in the report
comes from data and none from the LLM.
"""
import html

from sources.earnings import describe as describe_earnings


def last_move(prices: list[dict]) -> dict[str, float]:
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


def market_context(state: dict) -> dict:
    out = {}
    for ticker in ("SPY", "QQQ"):
        pm = (state.get("premarket") or {}).get(ticker)
        if pm:
            out[ticker] = {"session": pm["session"], "pct": round(pm["pct"], 1)}
    return out


def build_facts(state: dict) -> list[dict]:
    tradestie = {r["ticker"]: r for r in state.get("tradestie") or []}
    moves = last_move(state.get("prices") or [])
    facts = []
    for stock in state.get("trending") or []:
        ticker = stock["ticker"]
        t = tradestie.get(ticker)
        pm = (state.get("premarket") or {}).get(ticker)
        evidence = (state.get("evidence") or {}).get(ticker)
        sentiment = (state.get("sentiment") or {}).get(ticker)
        earnings = (state.get("earnings") or {}).get(ticker)
        facts.append({
            "ticker": ticker,
            "name": html.unescape(stock.get("name") or ""),
            "picked_by": stock["picked_by"],
            "mentions": stock.get("mentions"),
            "mentions_24h_ago": stock.get("mentions_24h_ago"),
            "tradestie": {"label": t["sentiment"].lower(), "score": t["sentiment_score"], "comments": t.get("no_of_comments")} if t else None,
            "prev_day_pct": round(moves[ticker], 1) if ticker in moves else None,
            "premarket": {"session": pm["session"], "pct": round(pm["pct"], 1)} if pm else None,
            "earnings": describe_earnings(earnings) if earnings else None,
            "reddit": {"source": evidence["source"], **(sentiment or {"n": 0})} if evidence else None,
            "headlines": [
                {"title": a["title"], "catalyst": a.get("catalyst"), "url": a.get("url")}
                for a in (state.get("news") or {}).get(ticker, [])[:3]
            ],
        })
    return facts
