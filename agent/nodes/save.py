import logging

from agent.errors import record_error
from agent.state import State
from agent.facts import build_facts
from db import save_brief, save_evidence, save_news, save_newsletter, save_pdf, save_prices, save_tradestie, save_trending

log = logging.getLogger(__name__)


def save(state: State) -> dict:
    """Write today's data to Neon. A failure is recorded, not raised, so the report still prints."""
    errors = []
    try:
        if state.get("top_tickers"):
            n = save_trending(state["top_tickers"], state.get("trending") or [])
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
        if state.get("evidence"):
            n = save_evidence(state["evidence"])
            log.info("Neon: saved %d rows to reddit_evidence", n)
        if state.get("brief") and not state.get("collect_only"):
            n = save_brief(state["brief"], build_facts(state), state.get("premarket") or {}, bool(state.get("errors")))
            log.info("Neon: saved %d rows to brief_picks", n)
        # Only a complete report is stored, so a rerun never reuses one with gaps.
        if state.get("errors"):
            log.warning("Neon: report not stored because earlier stages had errors")
        elif state.get("collect_only"):
            log.info("Neon: report not stored (collect-only run)")
        else:
            save_newsletter(state["newsletter"])
            log.info("Neon: saved today's report")
            if state.get("pdf") and save_pdf(state["pdf"]):
                log.info("Neon bucket: archived today's PDF")
    except Exception as e:
        errors.append(record_error("db", e))
    return {"errors": errors}
