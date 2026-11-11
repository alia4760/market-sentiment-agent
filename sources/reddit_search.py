"""Reddit posts and comments about a specific ticker.

Primary: Arctic Shift, a free community archive of Reddit (flaky: it times out under load, so
calls retry). Fallback: Tavily restricted to reddit.com (snippets only, no votes or dates).
"""
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

BASE = "https://arctic-shift.photon-reddit.com/api"
HEADERS = {"User-Agent": "market-sentiment-agent/0.1"}
REMOVED = {"[removed]", "[deleted]"}


def _get(path: str, params: dict, attempts: int = 3) -> list[dict]:
    """GET from Arctic Shift, retrying on timeouts (HTTP 422), rate limits and network errors."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(f"{BASE}/{path}", params=params, headers=HEADERS, timeout=60)
            if response.status_code == 200:
                return response.json().get("data") or []
            last = RuntimeError(f"Arctic Shift HTTP {response.status_code}: {response.text[:100]}")
        except requests.RequestException as e:
            last = e
        if attempt < attempts:
            time.sleep(3 * attempt)
    raise last


def mentions_ticker(text: str, ticker: str) -> bool:
    """True if the text names the ticker as a word (or $TICKER). Short tickers must be uppercase."""
    flags = re.IGNORECASE if len(ticker) >= 4 else 0
    return bool(re.search(rf"(?<![A-Za-z])\$?{re.escape(ticker)}(?![A-Za-z])", text, flags))


def _created(item: dict) -> str | None:
    """When the post or comment was written, as an ISO timestamp in UTC."""
    return datetime.fromtimestamp(item["created_utc"], timezone.utc).isoformat() if item.get("created_utc") else None


def _url(item: dict) -> str | None:
    return f"https://www.reddit.com{item['permalink']}" if item.get("permalink") else None


def search_ticker(
    ticker: str, hours: int = 24, max_posts: int = 4, max_comments: int = 8
) -> dict[str, list[dict]]:
    """Top WSB posts and comments mentioning the ticker in the last `hours` (24 by default), by upvotes."""
    after = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = []
    for p in _get("posts/search", {"subreddit": "wallstreetbets", "query": ticker, "after": after, "limit": 100}):
        text = f"{p.get('title', '')}\n{p.get('selftext') or ''}"
        if p.get("removed_by_category") or not mentions_ticker(text, ticker):
            continue
        body = "" if (p.get("selftext") or "") in REMOVED else p.get("selftext") or ""
        posts.append({"id": p["id"], "title": p["title"], "body": body, "score": p.get("score", 0),
                      "num_comments": p.get("num_comments", 0), "url": _url(p), "created": _created(p)})
    time.sleep(1)
    comments = []
    for c in _get("comments/search", {"subreddit": "wallstreetbets", "body": ticker, "after": after, "limit": 100}):
        body = c.get("body") or ""
        if body in REMOVED or len(body) < 20 or not mentions_ticker(body, ticker):
            continue
        comments.append({"id": c["id"], "body": body, "score": c.get("score", 0), "url": _url(c), "created": _created(c)})
    by_score = lambda x: x["score"]
    return {
        "posts": sorted(posts, key=by_score, reverse=True)[:max_posts],
        "comments": sorted(comments, key=by_score, reverse=True)[:max_comments],
    }


def search_ticker_tavily(ticker: str, name: str = "", max_results: int = 5) -> dict[str, list[dict]]:
    """Fallback: Reddit threads about the ticker found through Tavily (snippets, no vote counts)."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(
        f"wallstreetbets {name} {ticker} stock".replace("  ", " "),
        include_domains=["reddit.com"],
        time_range="day",
        max_results=max_results,
        search_depth="basic",
    )
    posts = [
        {"id": r["url"], "title": r["title"], "body": (r.get("content") or "")[:600],
         "score": None, "num_comments": None, "url": r["url"], "created": None}
        for r in response.get("results", [])
        if "/comments/" in r["url"]
    ]
    return {"posts": posts, "comments": []}
