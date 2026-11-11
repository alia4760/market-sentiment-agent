import logging

from agent.errors import record_error
from agent.state import State
from db import save_news, save_newsletter, save_post_scores, save_prices, save_tradestie, save_trending

log = logging.getLogger(__name__)


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
        errors.append(record_error("db", e))
    return {"errors": errors}
