from db.connection import get_db, today
from db.schema import ensure_tables

INSERT = """
insert into reddit_evidence
    (run_date, ticker, kind, item_id, source, title, body, score, num_comments, url, label, confidence, created_at)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict do nothing
"""


def save_evidence(evidence: dict[str, dict]) -> int:
    """Replace today's Reddit posts and comments, with their Jev labels when scored."""
    rows = [
        (
            today(), ticker, kind, str(item["id"]), entry["source"], item.get("title"),
            item.get("body"), item.get("score"), item.get("num_comments"), item.get("url"),
            item.get("label"), item.get("confidence"), item.get("created"),
        )
        for ticker, entry in evidence.items()
        for kind, group in (("post", entry["posts"]), ("comment", entry["comments"]))
        for item in group
    ]
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute("delete from reddit_evidence where run_date = %s", (today(),))
        with conn.cursor() as cur:
            cur.executemany(INSERT, rows)
    return len(rows)
