import logging

from agent.errors import record_error
from agent.jev import classify_sentiment
from agent.state import State
from sources.reddit import WSBPost

log = logging.getLogger(__name__)


def _post_text(post: WSBPost) -> str:
    return f"{post['title']}\n\n{post['body'][:1500]}".strip()


def score(state: State) -> dict:
    posts = state.get("posts") or []
    if state.get("collect_only"):
        log.info("Jev: skipped (collect-only run)")
        return {}
    if not posts:
        log.warning("Jev: no posts to score")
        return {}
    try:
        log.info("Jev: scoring %d posts", len(posts))
        results = classify_sentiment([_post_text(post) for post in posts])
    except Exception as e:
        return {"errors": [record_error("jev", e)]}
    scores = [
        {"title": post["title"], "url": post["url"], **result}
        for post, result in zip(posts, results)
    ]
    log.info("Jev: scored %d posts", len(scores))
    return {"scores": scores}
