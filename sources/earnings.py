import logging
from datetime import date, timedelta

import yfinance as yf

log = logging.getLogger(__name__)


def get_earnings_dates(tickers: list[str]) -> dict[str, date]:
    """Next (or just-reported) earnings date per ticker, from yfinance.

    Tickers without one (ETFs, odd symbols, lookup failures) are left out and logged.
    Only dates from 3 days ago onward count, so a stale past date isn't shown as upcoming.
    """
    cutoff = date.today() - timedelta(days=3)
    found, missing = {}, []
    for ticker in tickers:
        try:
            dates = yf.Ticker(ticker).calendar.get("Earnings Date") or []
            upcoming = sorted(d for d in dates if d >= cutoff)
            if upcoming:
                found[ticker] = upcoming[0]
            else:
                missing.append(ticker)
        except Exception as e:
            log.warning("earnings lookup failed for %s: %s", ticker, e)
            missing.append(ticker)
    if missing:
        log.info("yfinance: no earnings date for %s", ", ".join(missing))
    return found


def describe(day: date) -> str:
    days = (day - date.today()).days
    if days < 0:
        return f"reported {day:%b} {day.day}"
    if days == 0:
        return "reports today"
    if days <= 7:
        return f"reports {day:%b} {day.day} (in {days}d)"
    return f"next {day:%b} {day.day}"
