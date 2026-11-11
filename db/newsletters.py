from datetime import date

from db.connection import get_db, today
from db.schema import ensure_tables

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
