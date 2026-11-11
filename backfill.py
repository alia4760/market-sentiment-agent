"""Backfill Tradestie history and prices into Neon.

Usage: uv run backfill.py [--days 365]

Tradestie allows 20 requests/min anonymously, so this sleeps between calls (~3 s each).
Dates already in the database are skipped, so it is safe to rerun.
"""
import argparse
import time
from datetime import timedelta

from sources.prices import get_prices
from db import save_prices, save_tradestie, today, tradestie_dates
from sources.tradestie import get_tradestie

MIN_ROWS = 10  # skip days where Tradestie returns a near-empty list


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    have = tradestie_dates()
    tickers: set[str] = set()
    saved = skipped = 0
    for i in range(args.days, 0, -1):
        day = today() - timedelta(days=i)
        if day in have:
            continue
        try:
            rows = get_tradestie(day.isoformat())
        except Exception as e:
            print(f"{day}: failed ({e})")
            time.sleep(3.1)
            continue
        if len(rows) < MIN_ROWS:
            print(f"{day}: only {len(rows)} rows, skipped")
            skipped += 1
        else:
            save_tradestie(rows, day)
            tickers |= {r["ticker"] for r in rows}
            saved += 1
            if saved % 20 == 0:
                print(f"{day}: {saved} days saved so far")
        time.sleep(3.1)

    print(f"Tradestie: {saved} days saved, {skipped} skipped")
    if tickers:
        start = today() - timedelta(days=args.days + 7)
        prices = get_prices(sorted(tickers), start=start.isoformat(), end=today().isoformat())
        print(f"Prices: saved {save_prices(prices)} rows for {len(tickers)} tickers")


if __name__ == "__main__":
    main()
