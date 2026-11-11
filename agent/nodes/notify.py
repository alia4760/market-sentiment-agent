import logging
import os

from agent.errors import record_error
from agent.report import short_message, to_pdf
from agent.state import State
from db import get_pdf, get_sent_at, mark_sent, today
from sources.discord import send_brief, send_report

log = logging.getLogger(__name__)


def notify(state: State) -> dict:
    """Send the report to Discord once per day: a short message plus the PDF.

    The PDF is the one just rendered, or on a rerun the one archived in the bucket (rebuilt from
    the stored text if there is none). If no PDF can be made, the full text is sent instead.
    """
    if state.get("collect_only"):
        return {}
    if not os.environ.get("DISCORD_WEBHOOK_URL"):
        log.info("Discord: DISCORD_WEBHOOK_URL is not set; not sending the report")
        return {}
    text = state.get("newsletter")
    if not text:
        return {}
    try:
        if not state.get("resend") and get_sent_at():
            log.info("Discord: today's report was already sent; skipping (use --resend to send again)")
            return {}
        pdf = state.get("pdf")
        if pdf is None:
            pdf = get_pdf()
            if pdf:
                log.info("Discord: using the PDF archived in the bucket")
        if pdf is None:
            try:
                pdf = to_pdf(text)
                log.info("Discord: no archived PDF; rebuilt it from the stored report")
            except Exception as e:
                log.warning("Discord: could not build a PDF (%s); sending the text instead", e)
        if pdf:
            send_brief(short_message(text), pdf, f"market-brief-{today()}.pdf")
            log.info("Discord: sent the short message with the PDF attached")
        else:
            log.info("Discord: sent the report in %d message(s)", send_report(text))
        mark_sent()
    except Exception as e:
        return {"errors": [record_error("discord", e)]}
    return {}
