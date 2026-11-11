from datetime import date

import logging
import os

from db.connection import BUCKET, get_bucket_client, get_db, today
from db.schema import ensure_tables

log = logging.getLogger(__name__)

UPSERT_NEWSLETTER = """
insert into newsletters (run_date, text) values (%s, %s)
on conflict (run_date) do update set text = excluded.text, created_at = now()
"""


def get_newsletter(run_date: date | None = None) -> str | None:
    with get_db() as conn:
        ensure_tables(conn)
        row = conn.execute(
            "select text from newsletters where run_date = %s", (run_date or today(),)
        ).fetchone()
    return row[0] if row else None


def save_newsletter(text: str) -> None:
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(UPSERT_NEWSLETTER, (today(), text))


def get_sent_at(run_date: date | None = None):
    """When today's report was sent to Discord, or None if it has not been."""
    with get_db() as conn:
        ensure_tables(conn)
        row = conn.execute(
            "select sent_at from newsletters where run_date = %s", (run_date or today(),)
        ).fetchone()
    return row[0] if row else None


def mark_sent() -> None:
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute("update newsletters set sent_at = now() where run_date = %s", (today(),))


def save_pdf(pdf: bytes) -> bool:
    """Upload today's PDF to the Neon bucket and record its key. Skipped if no bucket credentials."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        log.warning("Bucket: AWS_ACCESS_KEY_ID is not set; the PDF is not archived")
        return False
    key = f"briefs/{today()}.pdf"
    get_bucket_client().put_object(Bucket=BUCKET, Key=key, Body=pdf, ContentType="application/pdf")
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute("update newsletters set pdf_key = %s where run_date = %s", (key, today()))
    return True


def get_pdf() -> bytes | None:
    """Today's archived PDF from the bucket, or None if there is none (or no bucket access)."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        return None
    try:
        with get_db() as conn:
            ensure_tables(conn)
            row = conn.execute("select pdf_key from newsletters where run_date = %s", (today(),)).fetchone()
        if not row or not row[0]:
            return None
        return get_bucket_client().get_object(Bucket=BUCKET, Key=row[0])["Body"].read()
    except Exception as e:
        log.warning("Bucket: could not read today's PDF: %s", e)
        return None
