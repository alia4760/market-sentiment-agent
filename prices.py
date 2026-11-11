import logging
from datetime import time

import yfinance as yf

log = logging.getLogger(__name__)


def get_prices(tickers: list[str], period: str = "5d", start=None, end=None) -> list[dict]:
    """Daily close and volume for many tickers in one batched yfinance call.

    Tickers with no data (delisted, odd symbols) are skipped. Raises if nothing comes back.
    Close is split/dividend adjusted (yfinance default).
    """
    tickers = sorted(set(tickers))
    kwargs = {"start": start, "end": end} if start else {"period": period}
    df = yf.download(
        tickers, interval="1d", group_by="ticker", progress=False, threads=True, **kwargs
    )
    available = set(df.columns.get_level_values(0)) if len(df.columns) else set()
    rows = []
    missing = []
    for ticker in tickers:
        if ticker not in available:
            missing.append(ticker)
            continue
        sub = df[ticker][["Close", "Volume"]].dropna(subset=["Close"])
        if sub.empty:
            missing.append(ticker)
            continue
        for day, r in sub.iterrows():
            rows.append(
                {
                    "ticker": ticker,
                    "date": day.date(),
                    "close": float(r["Close"]),
                    "volume": int(r["Volume"]) if r["Volume"] == r["Volume"] else None,
                }
            )
    if missing:
        log.warning("yfinance had no data for %d tickers: %s", len(missing), ", ".join(missing))
    if not rows:
        raise RuntimeError("yfinance returned no prices")
    return rows


def get_premarket(tickers: list[str]) -> dict[str, dict]:
    """Latest price including pre-market and after-hours, against the last regular-session close.

    Uses 5-minute bars with extended hours (4:00-20:00 ET). The reference close is the last bar
    inside 9:30-16:00 ET, so both numbers come from the same unadjusted source. Extended-hours
    trading is thin, so treat the move as a hint. Tickers with no bars are skipped.
    """
    tickers = sorted(set(tickers))
    df = yf.download(
        tickers, period="5d", interval="5m", prepost=True,
        group_by="ticker", progress=False, threads=True,
    )
    available = set(df.columns.get_level_values(0)) if len(df.columns) else set()
    out = {}
    for ticker in tickers:
        if ticker not in available:
            continue
        close = df[ticker]["Close"].dropna()
        if close.empty:
            continue
        et = close.index.tz_convert("America/New_York")
        regular = close[[time(9, 30) <= t < time(16, 0) for t in et.time]]
        if regular.empty:
            continue
        prev_close, last = float(regular.iloc[-1]), float(close.iloc[-1])
        last_time = et[-1].time()
        session = "pre" if last_time < time(9, 30) else "post" if last_time >= time(16, 0) else "regular"
        out[ticker] = {
            "prev_close": prev_close,
            "last": last,
            "pct": (last / prev_close - 1) * 100,
            "session": session,
            "as_of": et[-1].isoformat(),
        }
    if not out:
        raise RuntimeError("yfinance returned no extended-hours prices")
    return out
