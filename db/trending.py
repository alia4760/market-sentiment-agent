from db.connection import get_db, to_int, today
from db.schema import ensure_tables

INSERT_TRENDING = """
insert into trending_snapshots
    (snapshot_date, ticker, name, rank, mentions, mentions_24h_ago, rank_24h_ago, upvotes, picked_by)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def save_trending(stocks: list[dict], candidates: list[dict]) -> int:
    """Save the full top-N ticker list for today, tagging the ones picked as candidates."""
    picked = {s["ticker"]: ",".join(s["picked_by"]) for s in candidates}
    rows = [
        (
            today(),
            s["ticker"],
            s.get("name"),
            to_int(s.get("rank")),
            to_int(s.get("mentions")),
            to_int(s.get("mentions_24h_ago")),
            to_int(s.get("rank_24h_ago")),
            to_int(s.get("upvotes")),
            picked.get(s["ticker"]),
        )
        for s in stocks
    ]
    with get_db() as conn:
        ensure_tables(conn)
        # Replace the whole day so a rerun can't leave stale tickers behind.
        conn.execute("delete from trending_snapshots where snapshot_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(INSERT_TRENDING, rows)
    return len(rows)
