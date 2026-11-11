import logging

from agent.errors import record_error
from agent.jev import classify_sentiment
from agent.state import State

log = logging.getLogger(__name__)

THIN = 5  # fewer scored items than this and the roll-up is marked thin


def _text(kind: str, item: dict) -> str:
    if kind == "post":
        return f"{item['title']}\n\n{item['body'][:1000]}".strip()
    return item["body"][:600]


def score_evidence(state: State) -> dict:
    """Jev labels every Reddit post and comment, then rolls the labels up per ticker."""
    if state.get("collect_only"):
        log.info("Jev: sentiment scoring skipped (collect-only run)")
        return {}
    evidence = state.get("evidence") or {}
    items = [
        (ticker, kind, item)
        for ticker, e in evidence.items()
        for kind, group in (("post", e["posts"]), ("comment", e["comments"]))
        for item in group
    ]
    if not items:
        log.warning("Jev: no Reddit evidence to score")
        return {}
    try:
        log.info("Jev: scoring %d Reddit posts and comments", len(items))
        results = classify_sentiment([_text(kind, item) for _, kind, item in items])
    except Exception as e:
        return {"errors": [record_error("jev", e)]}
    for (_, _, item), result in zip(items, results):
        item["label"], item["confidence"] = result["label"], result["confidence"]

    sentiment = {}
    for ticker, e in evidence.items():
        scored = [i for i in e["posts"] + e["comments"] if i.get("label")]
        if not scored:
            continue
        counts = {k: sum(i["label"] == k for i in scored) for k in ("bullish", "bearish", "neutral")}
        top_post = max(e["posts"], key=lambda p: p["score"] or 0, default=None)
        sentiment[ticker] = {
            "n": len(scored),
            **counts,
            "net": round((counts["bullish"] - counts["bearish"]) / len(scored), 2),
            "thin": len(scored) < THIN,
            "top_post": {"title": top_post["title"], "score": top_post["score"], "url": top_post["url"]} if top_post else None,
        }
    log.info("Jev: scored %d items across %d tickers", len(items), len(sentiment))
    return {"evidence": evidence, "sentiment": sentiment}
