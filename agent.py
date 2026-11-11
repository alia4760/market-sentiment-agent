from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import logging
import operator

from reddit import WSBPost, get_wsb_top_posts
from apewisdom import get_wsb_trending
from candidates import rank_candidates
from earnings import describe as describe_earnings, get_earnings_dates
from jev import classify_sentiment
from news import get_news
from prices import get_premarket, get_prices
from storage import (
    get_newsletter,
    save_news,
    save_newsletter,
    save_post_scores,
    save_prices,
    save_tradestie,
    save_trending,
)
from tradestie import get_tradestie

log = logging.getLogger(__name__)

# Process exit code per failing stage (0 = clean run). main.py exits with the first one.
EXIT_CODES = {"reddit": 2, "apewisdom": 3, "jev": 4, "db": 5, "tradestie": 6, "prices": 7, "premarket": 8, "earnings": 9, "tavily": 10}


class State(TypedDict):
    refresh: bool               # rebuild even if today's newsletter is stored
    collect_only: bool          # fetch and save data only; no Jev scoring, no newsletter stored
    from_store: bool            # newsletter came from the database
    posts: list[WSBPost]        # from reddit.py
    top_tickers: list[dict]     # full ApeWisdom top 50
    trending: list[dict]        # top candidates, merged from ApeWisdom and Tradestie
    tradestie: list[dict]       # Tradestie top 50: ticker, sentiment, sentiment_score, no_of_comments
    prices: list[dict]          # recent daily close/volume for every ticker seen
    premarket: dict             # ticker -> latest extended-hours price vs last regular close
    earnings: dict              # ticker -> next earnings date
    news: dict                  # ticker -> today's headlines from Tavily
    scores: list[dict]          # {"title", "url", "label", "confidence"}
    newsletter: str
    errors: Annotated[list[dict], operator.add]   # {"stage", "message"}
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def _error(stage: str, e: Exception) -> dict:
    log.error("%s failed: %s", stage, e, exc_info=e)
    return {"stage": stage, "message": str(e)}


def load_stored(state: State) -> dict:
    """If today's newsletter is already in the database, reuse it."""
    if state.get("refresh"):
        log.info("Refresh requested; skipping the stored-newsletter check")
        return {}
    try:
        text = get_newsletter()
    except Exception as e:
        return {"errors": [_error("db", e)]}
    if text:
        log.info("Found today's stored newsletter; reusing it (use --refresh to rebuild)")
        return {"newsletter": text, "from_store": True}
    log.info("No stored newsletter for today; running the full pipeline")
    return {}


def after_load(state: State) -> str:
    return END if state.get("from_store") else "fetch"


def fetch(state: State) -> dict:
    update: dict = {"errors": []}
    try:
        update["posts"] = get_wsb_top_posts()
        log.info("Reddit: fetched %d posts", len(update["posts"]))
    except Exception as e:
        update["errors"].append(_error("reddit", e))
    try:
        top = get_wsb_trending(limit=50)
        if not top:
            raise RuntimeError("ApeWisdom returned no tickers")
        update["top_tickers"] = top
        log.info("ApeWisdom: fetched %d tickers", len(top))
    except Exception as e:
        update["errors"].append(_error("apewisdom", e))
    try:
        update["tradestie"] = get_tradestie()
        log.info("Tradestie: fetched %d tickers", len(update["tradestie"]))
    except Exception as e:
        update["errors"].append(_error("tradestie", e))
    return update


def rank(state: State) -> dict:
    """Merge ApeWisdom and Tradestie into the top-10 shortlist."""
    if not state.get("top_tickers") and not state.get("tradestie"):
        return {}
    trending = rank_candidates(state.get("top_tickers") or [], state.get("tradestie") or [])
    log.info(
        "Ranked %d candidates: %s",
        len(trending), ", ".join(f"{c['ticker']}({'+'.join(c['picked_by'])})" for c in trending),
    )
    return {"trending": trending}


def fetch_prices(state: State) -> dict:
    tickers = {s["ticker"] for s in state.get("top_tickers") or []}
    tickers |= {r["ticker"] for r in state.get("tradestie") or []}
    if not tickers:
        log.warning("yfinance: no tickers to price (ApeWisdom and Tradestie both empty)")
        return {}
    update: dict = {"errors": []}
    try:
        log.info("yfinance: requesting prices for %d tickers", len(tickers))
        rows = get_prices(sorted(tickers))
        log.info("yfinance: got %d price rows for %d tickers", len(rows), len({r["ticker"] for r in rows}))
        update["prices"] = rows
    except Exception as e:
        update["errors"].append(_error("prices", e))
    shortlist = [c["ticker"] for c in state.get("trending") or []]
    if shortlist:
        try:
            log.info("yfinance: requesting extended-hours prices for %d candidates", len(shortlist))
            update["premarket"] = get_premarket(shortlist)
            log.info("yfinance: got extended-hours prices for %d candidates", len(update["premarket"]))
        except Exception as e:
            update["errors"].append(_error("premarket", e))
    return update


def fetch_earnings(state: State) -> dict:
    shortlist = [c["ticker"] for c in state.get("trending") or []]
    if not shortlist:
        return {}
    try:
        found = get_earnings_dates(shortlist)
        log.info("yfinance: earnings dates for %d of %d candidates", len(found), len(shortlist))
        return {"earnings": found}
    except Exception as e:
        return {"errors": [_error("earnings", e)]}


def research(state: State) -> dict:
    """Search today's news for the shortlist (one Tavily credit per ticker)."""
    shortlist = state.get("trending") or []
    if not shortlist:
        return {}
    try:
        log.info("Tavily: searching news for %d candidates", len(shortlist))
        news = get_news(shortlist)
        log.info("Tavily: %d articles across %d tickers", sum(len(v) for v in news.values()), len(news))
        return {"news": news}
    except Exception as e:
        return {"errors": [_error("tavily", e)]}


def _post_text(post: WSBPost) -> str:
    return f"{post['title']}\n\n{post['body'][:1500]}".strip()


def score(state: State) -> dict:
    posts = state.get("posts") or []
    if state.get("collect_only"):
        log.info("Jev: skipped (collect-only run)")
        return {}
    if not posts:
        log.warning("Jev: no posts to score")
        return {}
    try:
        log.info("Jev: scoring %d posts", len(posts))
        results = classify_sentiment([_post_text(post) for post in posts])
    except Exception as e:
        return {"errors": [_error("jev", e)]}
    scores = [
        {"title": post["title"], "url": post["url"], **result}
        for post, result in zip(posts, results)
    ]
    log.info("Jev: scored %d posts", len(scores))
    return {"scores": scores}


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


def save(state: State) -> dict:
    """Write today's data to Neon. A failure is recorded, not raised, so the newsletter still prints."""
    errors = []
    try:
        if state.get("top_tickers"):
            n = save_trending(state["top_tickers"], state["trending"])
            log.info("Neon: saved %d rows to trending_snapshots", n)
        if state.get("tradestie"):
            n = save_tradestie(state["tradestie"])
            log.info("Neon: saved %d rows to tradestie_snapshots", n)
        if state.get("prices"):
            n = save_prices(state["prices"])
            log.info("Neon: saved %d rows to daily_prices", n)
        if state.get("news"):
            n = save_news(state["news"])
            log.info("Neon: saved %d rows to ticker_news", n)
        if state.get("posts"):
            n = save_post_scores(state["posts"], state.get("scores") or [])
            log.info("Neon: saved %d rows to post_scores", n)
        # Only a complete newsletter is stored, so a rerun never reuses one with gaps.
        if state.get("errors"):
            log.warning("Neon: newsletter not stored because earlier stages had errors")
        elif state.get("collect_only"):
            log.info("Neon: newsletter not stored (collect-only run)")
        else:
            save_newsletter(state["newsletter"])
            log.info("Neon: saved today's newsletter")
    except Exception as e:
        errors.append(_error("db", e))
    return {"errors": errors}


graph = StateGraph(State)
graph.add_node("load_stored", load_stored)
graph.add_node("fetch", fetch)
graph.add_node("rank", rank)
graph.add_node("fetch_prices", fetch_prices)
graph.add_node("fetch_earnings", fetch_earnings)
graph.add_node("research", research)
graph.add_node("score", score)
graph.add_node("summarize", summarize)
graph.add_node("save", save)
graph.add_edge(START, "load_stored")
graph.add_conditional_edges("load_stored", after_load, ["fetch", END])
graph.add_edge("fetch", "rank")
graph.add_edge("rank", "fetch_prices")
graph.add_edge("fetch_prices", "fetch_earnings")
graph.add_edge("fetch_earnings", "research")
graph.add_edge("research", "score")
graph.add_edge("score", "summarize")
graph.add_edge("summarize", "save")
graph.add_edge("save", END)

agent = graph.compile()
