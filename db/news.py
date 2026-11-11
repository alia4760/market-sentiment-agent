from db.connection import get_db, today
from db.schema import ensure_tables


def save_news(news: dict[str, list[dict]]) -> int:
    """Replace today's saved headlines."""
    values = [
        (today(), ticker, a["url"], a["title"], a["content"], a["published"])
        for ticker, articles in news.items()
        for a in articles
    ]
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute("delete from ticker_news where run_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into ticker_news values (%s, %s, %s, %s, %s, %s) on conflict do nothing",
                values,
            )
    return len(values)
