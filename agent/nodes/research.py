import logging

from agent.errors import record_error
from agent.state import State
from sources.news import get_news

log = logging.getLogger(__name__)


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
        return {"errors": [record_error("tavily", e)]}
