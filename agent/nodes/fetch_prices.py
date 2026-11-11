import logging

from agent.errors import record_error
from agent.state import State
from sources.prices import get_premarket, get_prices

log = logging.getLogger(__name__)


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
        update["errors"].append(record_error("prices", e))
    shortlist = [c["ticker"] for c in state.get("trending") or []]
    if shortlist:
        shortlist += ["SPY", "QQQ"]  # market context for the report
        try:
            log.info("yfinance: requesting extended-hours prices for %d candidates", len(shortlist))
            update["premarket"] = get_premarket(shortlist)
            log.info("yfinance: got extended-hours prices for %d candidates", len(update["premarket"]))
        except Exception as e:
            update["errors"].append(record_error("premarket", e))
    return update
