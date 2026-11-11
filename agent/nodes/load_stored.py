import logging

from langgraph.graph import END

from agent.errors import record_error
from agent.state import State
from db import get_newsletter

log = logging.getLogger(__name__)


def load_stored(state: State) -> dict:
    """If today's newsletter is already in the database, reuse it."""
    if state.get("refresh"):
        log.info("Refresh requested; skipping the stored-newsletter check")
        return {}
    try:
        text = get_newsletter()
    except Exception as e:
        return {"errors": [record_error("db", e)]}
    if text:
        log.info("Found today's stored newsletter; reusing it (use --refresh to rebuild)")
        return {"newsletter": text, "from_store": True}
    log.info("No stored newsletter for today; running the full pipeline")
    return {}


def after_load(state: State) -> str:
    return END if state.get("from_store") else "fetch"
