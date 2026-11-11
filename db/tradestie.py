from datetime import date

from db.connection import get_db, to_int, today
from db.schema import ensure_tables


def save_tradestie(rows: list[dict], snapshot_date: date | None = None) -> int:
    """Replace one day's Tradestie snapshot (defaults to today, UTC)."""
    day = snapshot_date or today()
    values = [
        (day, r["ticker"], r.get("sentiment"), r.get("sentiment_score"), to_int(r.get("no_of_comments")))
        for r in rows
    ]
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute("delete from tradestie_snapshots where snapshot_date = %s", (day,))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into tradestie_snapshots values (%s, %s, %s, %s, %s)", values
            )
    return len(values)


def tradestie_dates() -> set[date]:
    with get_db() as conn:
        ensure_tables(conn)
        return {r[0] for r in conn.execute("select distinct snapshot_date from tradestie_snapshots")}
