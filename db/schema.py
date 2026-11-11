import psycopg

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
    create table if not exists ticker_news (
        run_date date not null,
        ticker text not null,
        url text not null,
        title text,
        content text,
        published text,
        primary key (run_date, ticker, url)
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


def ensure_tables(conn: psycopg.Connection) -> None:
    for ddl in TABLES:
        conn.execute(ddl)
