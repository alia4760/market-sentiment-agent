from datetime import datetime, timezone

from apewisdom import get_wsb_trending, pick_candidates
from storage import get_db

CREATE_TABLE = """
create table if not exists trending_snapshots (
    snapshot_date date not null,
    ticker text not null,
    name text,
    rank int,
    mentions int,
    mentions_24h_ago int,
    rank_24h_ago int,
    upvotes int,
    picked_by text,
    primary key (snapshot_date, ticker)
)
"""

UPSERT = """
insert into trending_snapshots
    (snapshot_date, ticker, name, rank, mentions, mentions_24h_ago, rank_24h_ago, upvotes, picked_by)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (snapshot_date, ticker) do update set
    name = excluded.name,
    rank = excluded.rank,
    mentions = excluded.mentions,
    mentions_24h_ago = excluded.mentions_24h_ago,
    rank_24h_ago = excluded.rank_24h_ago,
    upvotes = excluded.upvotes,
    picked_by = excluded.picked_by
"""


def _int(value) -> int | None:
    return int(value) if value is not None else None


def save_trending_snapshot(limit: int = 50) -> int:
    stocks = get_wsb_trending(limit=limit)
    if not stocks:
        raise RuntimeError("ApeWisdom returned no tickers; nothing saved")

    picked = {s["ticker"]: ",".join(s["picked_by"]) for s in pick_candidates(stocks)}
    today = datetime.now(timezone.utc).date()
    rows = [
        (
            today,
            s["ticker"],
            s.get("name"),
            _int(s.get("rank")),
            _int(s.get("mentions")),
            _int(s.get("mentions_24h_ago")),
            _int(s.get("rank_24h_ago")),
            _int(s.get("upvotes")),
            picked.get(s["ticker"]),
        )
        for s in stocks
    ]

    with get_db() as conn:
        conn.execute(CREATE_TABLE)
        with conn.cursor() as cur:
            cur.executemany(UPSERT, rows)
    return len(rows)


if __name__ == "__main__":
    count = save_trending_snapshot()
    print(f"Saved {count} tickers for {datetime.now(timezone.utc).date()}")
