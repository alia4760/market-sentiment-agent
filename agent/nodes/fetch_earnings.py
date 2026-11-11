import logging

from agent.errors import record_error
from agent.state import State
from sources.earnings import get_earnings_dates

log = logging.getLogger(__name__)


def fetch_earnings(state: State) -> dict:
    shortlist = [c["ticker"] for c in state.get("trending") or []]
    if not shortlist:
        return {}
    try:
        found = get_earnings_dates(shortlist)
        log.info("yfinance: earnings dates for %d of %d candidates", len(found), len(shortlist))
        return {"earnings": found}
    except Exception as e:
        return {"errors": [record_error("earnings", e)]}
