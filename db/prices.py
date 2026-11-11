from db.connection import get_db
from db.schema import ensure_tables


def save_prices(rows: list[dict]) -> int:
    """Upsert daily prices; past prices are facts, so newer data just overwrites."""
    values = [(r["date"], r["ticker"], r["close"], r["volume"]) for r in rows]
    with get_db() as conn:
        ensure_tables(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """insert into daily_prices (price_date, ticker, close, volume)
                   values (%s, %s, %s, %s)
                   on conflict (price_date, ticker) do update set
                       close = excluded.close, volume = excluded.volume""",
                values,
            )
    return len(values)
