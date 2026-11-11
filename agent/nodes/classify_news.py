import logging

from agent.errors import record_error
from agent.jev import classify_catalyst
from agent.state import State

log = logging.getLogger(__name__)

HEADLINES_PER_TICKER = 3


def classify_news(state: State) -> dict:
    """Jev labels each top headline with its catalyst (earnings, analyst, deal, legal, macro...)."""
    if state.get("collect_only"):
        log.info("Jev: catalyst labelling skipped (collect-only run)")
        return {}
    news = state.get("news") or {}
    articles = [a for items in news.values() for a in items[:HEADLINES_PER_TICKER]]
    if not articles:
        return {}
    try:
        log.info("Jev: labelling %d headlines", len(articles))
        results = classify_catalyst([a["title"] for a in articles])
    except Exception as e:
        return {"errors": [record_error("jev", e)]}
    for article, result in zip(articles, results):
        article["catalyst"] = result["label"]
    return {"news": news}
