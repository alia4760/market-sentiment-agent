import html
import logging
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
log = logging.getLogger(__name__)


def get_news(candidates: list[dict], max_results: int = 4) -> dict[str, list[dict]]:
    """Today's headlines for each candidate from Tavily (1 credit per ticker).

    Per-ticker failures are logged and skipped. Raises only if every search failed,
    so a bad key or exhausted quota shows up as an error instead of an empty report.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    news: dict[str, list[dict]] = {}
    failures, last_error = 0, None
    for stock in candidates:
        ticker = stock["ticker"]
        name = html.unescape(stock.get("name") or "")
        try:
            response = client.search(
                f"{name} {ticker} stock".strip(),
                topic="news",
                time_range="day",
                max_results=max_results,
                search_depth="basic",
                exclude_domains=["tavily.com"],
            )
            news[ticker] = [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "content": (r.get("content") or "")[:500],
                    "published": r.get("published_date"),
                }
                for r in response.get("results", [])
            ]
        except Exception as e:
            failures, last_error = failures + 1, e
            log.warning("Tavily search failed for %s: %s", ticker, e)
    if candidates and failures == len(candidates):
        raise RuntimeError(f"all Tavily searches failed; last error: {last_error}")
    return news
