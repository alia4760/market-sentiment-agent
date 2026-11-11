import logging

from agent.errors import record_error
from agent.state import State
from sources.apewisdom import get_wsb_trending
from sources.reddit import get_wsb_top_posts
from sources.tradestie import get_tradestie

log = logging.getLogger(__name__)


def fetch(state: State) -> dict:
    update: dict = {"errors": []}
    try:
        update["posts"] = get_wsb_top_posts()
        log.info("Reddit: fetched %d posts", len(update["posts"]))
    except Exception as e:
        update["errors"].append(record_error("reddit", e))
    try:
        top = get_wsb_trending(limit=50)
        if not top:
            raise RuntimeError("ApeWisdom returned no tickers")
        update["top_tickers"] = top
        log.info("ApeWisdom: fetched %d tickers", len(top))
    except Exception as e:
        update["errors"].append(record_error("apewisdom", e))
    try:
        update["tradestie"] = get_tradestie()
        log.info("Tradestie: fetched %d tickers", len(update["tradestie"]))
    except Exception as e:
        update["errors"].append(record_error("tradestie", e))
    return update
