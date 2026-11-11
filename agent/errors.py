import logging

log = logging.getLogger(__name__)


def record_error(stage: str, e: Exception) -> dict:
    """Log an error with its traceback and return the entry to add to the state's errors."""
    log.error("%s failed: %s", stage, e, exc_info=e)
    return {"stage": stage, "message": str(e)}
