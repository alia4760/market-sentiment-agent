import logging

from agent.errors import record_error
from agent.report import to_pdf
from agent.state import State

log = logging.getLogger(__name__)


def render_pdf(state: State) -> dict:
    """Render the finished report as a formatted PDF."""
    if state.get("collect_only") or not state.get("newsletter"):
        return {}
    try:
        pdf = to_pdf(state["newsletter"])
        log.info("PDF: rendered the report (%d KB)", len(pdf) // 1024)
        return {"pdf": pdf}
    except Exception as e:
        return {"errors": [record_error("pdf", e)]}
