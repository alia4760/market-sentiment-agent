import requests

URL = "https://tradestie.com/api/v1/apps/reddit"


def get_tradestie(date: str | None = None) -> list[dict]:
    """Top ~50 WSB tickers with Tradestie's sentiment label, score and comment count.

    Pass date="YYYY-MM-DD" for a past day. Raises if the API returns nothing.
    """
    response = requests.get(
        URL,
        params={"date": date} if date else None,
        headers={"User-Agent": "market-sentiment-agent/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise RuntimeError(f"Tradestie returned no tickers (date={date})")
    return rows
