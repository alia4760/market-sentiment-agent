import logging

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
