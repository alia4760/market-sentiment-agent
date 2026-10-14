import html
import re

import feedparser
from typing_extensions import TypedDict


class WSBPost(TypedDict):
    rank: int
    title: str
    url: str
    published: str
    author: str
    body: str


def _extract_body(summary_html: str) -> str:
    match = re.search(r'<div class="md">(.*?)</div>', summary_html, re.DOTALL)
    if not match:
        return ""
    text = re.sub(r"<[^>]+>", " ", match.group(1))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def get_wsb_top_posts(limit: int = 10) -> list[WSBPost]:
    """Fetch the top posts from r/wallstreetbets via RSS."""
    feed = feedparser.parse(
        "https://www.reddit.com/r/wallstreetbets/top/.rss?t=day",
        request_headers={"User-Agent": "market-sentiment-agent/0.1"},
    )

    posts = []
    for i, entry in enumerate(feed.entries[:limit]):
        posts.append(
            WSBPost(
                rank=i + 1,
                title=entry.title,
                url=entry.link,
                published=entry.get("published", "N/A"),
                author=entry.get("author", "N/A"),
                body=_extract_body(entry.get("summary", "")),
            )
        )
    return posts


if __name__ == "__main__":
    posts = get_wsb_top_posts()
    for post in posts:
        print(f"#{post['rank']} {post['title']}")
        print(f"  {post['url']}\n")
