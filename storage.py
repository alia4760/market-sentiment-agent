import os
from datetime import date, datetime, timezone

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()

BUCKET = "assets"

TABLES = [
    """
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
    """,
    """
    create table if not exists post_scores (
        run_date date not null,
        url text not null,
        rank int,
        title text,
        author text,
        body text,
        label text,
        confidence double precision,
        primary key (run_date, url)
    )
    """,
    """
    create table if not exists tradestie_snapshots (
        snapshot_date date not null,
        ticker text not null,
        sentiment text,
        sentiment_score double precision,
        comments int,
        primary key (snapshot_date, ticker)
    )
    """,
    """
    create table if not exists daily_prices (
        price_date date not null,
        ticker text not null,
        close double precision,
        volume bigint,
        primary key (price_date, ticker)
    )
    """,
    """
    create table if not exists newsletters (
        run_date date primary key,
        text text not null,
        created_at timestamptz not null default now(),
        sent_at timestamptz
    )
    """,
]

INSERT_TRENDING = """
insert into trending_snapshots
    (snapshot_date, ticker, name, rank, mentions, mentions_24h_ago, rank_24h_ago, upvotes, picked_by)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

INSERT_POST = """
insert into post_scores (run_date, url, rank, title, author, body, label, confidence)
values (%s, %s, %s, %s, %s, %s, %s, %s)
"""

# sent_at is left alone on conflict so a rebuild can't cause a second email by itself
UPSERT_NEWSLETTER = """
insert into newsletters (run_date, text) values (%s, %s)
on conflict (run_date) do update set text = excluded.text, created_at = now()
"""


def get_db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def get_bucket_client():
    return boto3.client("s3")


def today() -> date:
    return datetime.now(timezone.utc).date()


def _int(value) -> int | None:
    return int(value) if value is not None else None


def _ensure_tables(conn: psycopg.Connection) -> None:
    for ddl in TABLES:
        conn.execute(ddl)


def save_trending(stocks: list[dict], candidates: list[dict]) -> int:
    """Save the full top-N ticker list for today, tagging the ones picked as candidates."""
    picked = {s["ticker"]: ",".join(s["picked_by"]) for s in candidates}
    rows = [
        (
            today(),
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
        _ensure_tables(conn)
        # Replace the whole day so a rerun can't leave stale tickers behind.
        conn.execute("delete from trending_snapshots where snapshot_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(INSERT_TRENDING, rows)
    return len(rows)


def save_post_scores(posts: list[dict], scores: list[dict]) -> int:
    """Save today's posts with their Jev labels (label is null if scoring failed)."""
    by_url = {s["url"]: s for s in scores}
    rows = [
        (
            today(),
            p["url"],
            p["rank"],
            p["title"],
            p["author"],
            p["body"],
            by_url.get(p["url"], {}).get("label"),
            by_url.get(p["url"], {}).get("confidence"),
        )
        for p in posts
    ]
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute("delete from post_scores where run_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(INSERT_POST, rows)
    return len(rows)


def save_tradestie(rows: list[dict], snapshot_date: date | None = None) -> int:
    """Replace one day's Tradestie snapshot (defaults to today, UTC)."""
    day = snapshot_date or today()
    values = [
        (day, r["ticker"], r.get("sentiment"), r.get("sentiment_score"), _int(r.get("no_of_comments")))
        for r in rows
    ]
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute("delete from tradestie_snapshots where snapshot_date = %s", (day,))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into tradestie_snapshots values (%s, %s, %s, %s, %s)", values
            )
    return len(values)


def tradestie_dates() -> set[date]:
    with get_db() as conn:
        _ensure_tables(conn)
        return {r[0] for r in conn.execute("select distinct snapshot_date from tradestie_snapshots")}


def save_prices(rows: list[dict]) -> int:
    """Upsert daily prices; past prices are facts, so newer data just overwrites."""
    values = [(r["date"], r["ticker"], r["close"], r["volume"]) for r in rows]
    with get_db() as conn:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.executemany(
                """insert into daily_prices (price_date, ticker, close, volume)
                   values (%s, %s, %s, %s)
                   on conflict (price_date, ticker) do update set
                       close = excluded.close, volume = excluded.volume""",
                values,
            )
    return len(values)


def get_newsletter(run_date: date | None = None) -> str | None:
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "select text from newsletters where run_date = %s", (run_date or today(),)
        ).fetchone()
    return row[0] if row else None


def save_newsletter(text: str) -> None:
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute(UPSERT_NEWSLETTER, (today(), text))
