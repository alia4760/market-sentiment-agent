import logging

from agent.errors import record_error
from agent.state import State
from sources.apewisdom import get_wsb_trending
from sources.tradestie import get_tradestie

log = logging.getLogger(__name__)


def fetch(state: State) -> dict:
    """Pull the two attention lists: ApeWisdom mentions and Tradestie comments and sentiment."""
    update: dict = {"errors": []}
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
