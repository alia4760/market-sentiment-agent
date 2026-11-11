from db.connection import get_db, today
from db.schema import ensure_tables

INSERT_POST = """
insert into post_scores (run_date, url, rank, title, author, body, label, confidence)
values (%s, %s, %s, %s, %s, %s, %s, %s)
"""


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
        ensure_tables(conn)
        conn.execute("delete from post_scores where run_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(INSERT_POST, rows)
    return len(rows)
