import html
import logging
import time

from agent.errors import record_error
from agent.state import State
from sources.reddit_search import search_ticker, search_ticker_tavily

log = logging.getLogger(__name__)


def reddit_evidence(state: State) -> dict:
    """Find WSB posts and comments about each candidate: Arctic Shift first, Tavily as a backup."""
    shortlist = state.get("trending") or []
    if not shortlist:
        return {}
    evidence: dict = {}
    raised = 0
    for stock in shortlist:
        ticker, name = stock["ticker"], html.unescape(stock.get("name") or "")
        entry = {"source": "none", "posts": [], "comments": []}
        try:
            found = search_ticker(ticker, name)
            if found["posts"] or found["comments"]:
                entry = {"source": "arctic", **found}
        except Exception as e:
            raised += 1
            log.warning("Arctic Shift failed for %s: %s", ticker, e)
        if entry["source"] == "none":
            try:
                found = search_ticker_tavily(ticker, name)
                if found["posts"]:
                    entry = {"source": "tavily", **found}
            except Exception as e:
                raised += 1
                log.warning("Tavily Reddit search failed for %s: %s", ticker, e)
        evidence[ticker] = entry
        log.info(
            "Reddit %s: %s, %d posts, %d comments",
            ticker, entry["source"], len(entry["posts"]), len(entry["comments"]),
        )
        time.sleep(1)
    if all(e["source"] == "none" for e in evidence.values()) and raised:
        err = RuntimeError("no Reddit evidence for any ticker; Arctic Shift and Tavily failed or were empty")
        return {"evidence": evidence, "errors": [record_error("reddit", err)]}
    return {"evidence": evidence}
