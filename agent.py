from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import logging
import operator

from reddit import WSBPost, get_wsb_top_posts
from apewisdom import get_wsb_trending, pick_candidates
from jev import classify_sentiment
from storage import get_newsletter, save_newsletter, save_post_scores, save_trending

log = logging.getLogger(__name__)

# Process exit code per failing stage (0 = clean run). main.py exits with the first one.
EXIT_CODES = {"reddit": 2, "apewisdom": 3, "jev": 4, "db": 5}


class State(TypedDict):
    refresh: bool               # rebuild even if today's newsletter is stored
    from_store: bool            # newsletter came from the database
    posts: list[WSBPost]        # from reddit.py
    top_tickers: list[dict]     # full ApeWisdom top 50
    trending: list[dict]        # candidates picked from top_tickers
    scores: list[dict]          # {"title", "url", "label", "confidence"}
    newsletter: str
    errors: Annotated[list[dict], operator.add]   # {"stage", "message"}
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def _error(stage: str, e: Exception) -> dict:
    log.error("%s failed: %s", stage, e)
    return {"stage": stage, "message": str(e)}


def load_stored(state: State) -> dict:
    """If today's newsletter is already in the database, reuse it."""
    if state.get("refresh"):
        return {}
    try:
        text = get_newsletter()
    except Exception as e:
        return {"errors": [_error("db", e)]}
    return {"newsletter": text, "from_store": True} if text else {}


def after_load(state: State) -> str:
    return END if state.get("from_store") else "fetch"


def fetch(state: State) -> dict:
    update: dict = {"errors": []}
    try:
        update["posts"] = get_wsb_top_posts()
    except Exception as e:
        update["errors"].append(_error("reddit", e))
    try:
        top = get_wsb_trending(limit=50)
        if not top:
            raise RuntimeError("ApeWisdom returned no tickers")
        update["top_tickers"] = top
        update["trending"] = pick_candidates(top)
    except Exception as e:
        update["errors"].append(_error("apewisdom", e))
    return update


def _post_text(post: WSBPost) -> str:
    return f"{post['title']}\n\n{post['body'][:1500]}".strip()


def score(state: State) -> dict:
    posts = state.get("posts") or []
    if not posts:
        return {}
    try:
        results = classify_sentiment([_post_text(post) for post in posts])
    except Exception as e:
        return {"errors": [_error("jev", e)]}
    scores = [
        {"title": post["title"], "url": post["url"], **result}
        for post, result in zip(posts, results)
    ]
    return {"scores": scores}


def summarize(state: State) -> dict:
    lines = ["=== Market Sentiment Newsletter ===", "", "Trending tickers:"]
    if state.get("trending"):
        for stock in state["trending"]:
            picked = "+".join(stock["picked_by"])
            lines.append(
                f"  {stock['ticker']}: {stock['mentions']} mentions "
                f"(was {stock.get('mentions_24h_ago', 'N/A')}) [{picked}]"
            )
    else:
        lines.append("  (unavailable today)")

    lines.append("")
    lines.append("WSB post sentiment:")
    if state.get("scores"):
        for item in state["scores"]:
            lines.append(f"  [{item['label']} ({item['confidence']:.2f})] {item['title']}")
    else:
        lines.append("  (unavailable today)")

    return {"newsletter": "\n".join(lines)}


def save(state: State) -> dict:
    """Write today's data to Neon. A failure is recorded, not raised, so the newsletter still prints."""
    errors = []
    try:
        if state.get("top_tickers"):
            save_trending(state["top_tickers"], state["trending"])
        if state.get("posts"):
            save_post_scores(state["posts"], state.get("scores") or [])
        # Only a complete newsletter is stored, so a rerun never reuses one with gaps.
        if not state.get("errors"):
            save_newsletter(state["newsletter"])
    except Exception as e:
        errors.append(_error("db", e))
    return {"errors": errors}


graph = StateGraph(State)
graph.add_node("load_stored", load_stored)
graph.add_node("fetch", fetch)
graph.add_node("score", score)
graph.add_node("summarize", summarize)
graph.add_node("save", save)
graph.add_edge(START, "load_stored")
graph.add_conditional_edges("load_stored", after_load, ["fetch", END])
graph.add_edge("fetch", "score")
graph.add_edge("score", "summarize")
graph.add_edge("summarize", "save")
graph.add_edge("save", END)

agent = graph.compile()
