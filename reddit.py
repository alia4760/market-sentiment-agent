import feedparser
from dataclasses import dataclass


@dataclass
class WSBPost:
    rank: int
    title: str
    url: str
    published: str
    author: str


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
            )
        )
    return posts


if __name__ == "__main__":
    posts = get_wsb_top_posts()
    for post in posts:
        print(f"#{post.rank} {post.title}")
        print(f"  {post.url}\n")
