import requests

EXCLUDED_TICKERS = {"SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "TQQQ", "SQQQ", "SPXL", "SPXS"}


def get_wsb_trending(limit: int = 10) -> list[dict]:
    """Fetch the top mentioned tickers on r/wallstreetbets."""
    url = "https://apewisdom.io/api/v1.0/filter/wallstreetbets"
    response = requests.get(url, headers={"User-Agent": "market-sentiment-agent/0.1"})
    response.raise_for_status()

    results = response.json().get("results", [])
    return results[:limit]


def pick_candidates(stocks: list[dict], n: int = 10, min_mentions: int = 10) -> list[dict]:
    """Top n by mentions plus top n by day-over-day change, excluding broad-market funds."""
    eligible = [s for s in stocks if s["ticker"].upper() not in EXCLUDED_TICKERS]

    def mentions(s: dict) -> int:
        return int(s.get("mentions") or 0)

    def previous(s: dict) -> int:
        return int(s.get("mentions_24h_ago") or 0)

    def change_key(s: dict) -> tuple[float, int]:
        return (mentions(s) / max(previous(s), 1), mentions(s) - previous(s))

    top_mentions = sorted(eligible, key=mentions, reverse=True)[:n]
    movers = [s for s in eligible if mentions(s) >= min_mentions]
    top_changed = sorted(movers, key=change_key, reverse=True)[:n]

    picked: dict[str, dict] = {}
    for reason, group in (("mentions", top_mentions), ("change", top_changed)):
        for stock in group:
            entry = picked.setdefault(stock["ticker"], {**stock, "picked_by": []})
            entry["picked_by"].append(reason)
    return list(picked.values())


def get_ticker_sentiment(ticker: str, filter: str = "wallstreetbets") -> dict | None:
    """Fetch mention and sentiment data for a specific ticker across all pages."""
    ticker = ticker.upper()
    page = 1
    while True:
        url = f"https://apewisdom.io/api/v1.0/filter/{filter}/page/{page}"
        response = requests.get(url, headers={"User-Agent": "market-sentiment-agent/0.1"})
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])
        if not results:
            return None

        for stock in results:
            if stock["ticker"].upper() == ticker:
                return stock

        if page >= data.get("pages", 1):
            return None
        page += 1


if __name__ == "__main__":
    print("=== Top 10 Trending on WSB ===")
    trending = get_wsb_trending()
    for stock in trending:
        print(
            f"Rank {stock['rank']}: {stock['ticker']} | "
            f"Mentions: {stock['mentions']} | "
            f"24h Change: {stock.get('mentions_24h_ago', 'N/A')} | "
            f"Upvotes: {stock.get('upvotes', 'N/A')}"
        )

    print("\n=== Individual Ticker Lookup: NVDA ===")
    result = get_ticker_sentiment("NVDA")
    if result:
        print(
            f"Rank {result['rank']}: {result['ticker']} | "
            f"Mentions: {result['mentions']} | "
            f"24h Change: {result.get('mentions_24h_ago', 'N/A')} | "
            f"Upvotes: {result.get('upvotes', 'N/A')}"
        )
    else:
        print("NVDA not found in current results.")
