import json

from db.connection import get_db, today
from db.schema import ensure_tables

UPSERT = """
insert into brief_picks
    (run_date, ticker, stance, horizon, summary, top_pick_rank, top_pick_direction, top_pick_reason,
     ref_price, ref_session, prev_close, model, prompt_hash, degraded, facts)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (run_date, ticker) do update set
    stance = excluded.stance, horizon = excluded.horizon, summary = excluded.summary,
    top_pick_rank = excluded.top_pick_rank, top_pick_direction = excluded.top_pick_direction,
    top_pick_reason = excluded.top_pick_reason, ref_price = excluded.ref_price,
    ref_session = excluded.ref_session, prev_close = excluded.prev_close, model = excluded.model,
    prompt_hash = excluded.prompt_hash, degraded = excluded.degraded, facts = excluded.facts
"""


def save_brief(brief: dict, facts: list[dict], premarket: dict, degraded: bool) -> int:
    """One row per ticker: the LLM's stance, horizon and take, whether it was a top pick, the price
    at report time, the facts it was given, and the model and prompt version. Queryable for later analysis."""
    stances = {t["ticker"]: t for t in brief.get("tickers", [])}
    picks = {p["ticker"]: (i, p) for i, p in enumerate(brief.get("top_picks", []), 1)}
    rows = []
    for f in facts:
        ticker = f["ticker"]
        t, (rank, pick) = stances.get(ticker, {}), picks.get(ticker, (None, {}))
        pm = (premarket or {}).get(ticker) or {}
        rows.append((
            today(), ticker, t.get("stance"), t.get("horizon"), t.get("summary"),
            rank, pick.get("direction"), pick.get("reason"),
            pm.get("last"), pm.get("session"), pm.get("prev_close"),
            brief.get("model"), brief.get("prompt_hash"), degraded, json.dumps(f, default=str),
        ))
    with get_db() as conn:
        ensure_tables(conn)
        with conn.cursor() as cur:
            cur.executemany(UPSERT, rows)
    return len(rows)
