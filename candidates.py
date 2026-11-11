from apewisdom import EXCLUDED_TICKERS, WORD_TICKERS, pick_candidates


def rank_candidates(ape: list[dict], tradestie: list[dict], n: int = 10) -> list[dict]:
    """Merge ApeWisdom and Tradestie into one ranked shortlist.

    A ticker is picked by each source that puts it near the top: ApeWisdom top mentions,
    ApeWisdom biggest change, Tradestie most comments. Tickers picked by more sources
    rank first (the sources converge), then by mentions. Funds and word-tickers are skipped.
    """
    picked = {s["ticker"]: s for s in pick_candidates(ape)}

    skip = EXCLUDED_TICKERS | WORD_TICKERS
    eligible = [r for r in tradestie if r["ticker"].upper() not in skip]
    top_comments = sorted(eligible, key=lambda r: r.get("no_of_comments") or 0, reverse=True)[:10]
    ape_by_ticker = {s["ticker"]: s for s in ape}
    for row in top_comments:
        entry = picked.get(row["ticker"])
        if entry is None:
            entry = {**ape_by_ticker.get(row["ticker"], {"ticker": row["ticker"]}), "picked_by": []}
            picked[row["ticker"]] = entry
        entry["picked_by"].append("tradestie")

    tradestie_by_ticker = {r["ticker"]: r for r in tradestie}
    for entry in picked.values():
        entry["tradestie"] = tradestie_by_ticker.get(entry["ticker"])

    ranked = sorted(
        picked.values(),
        key=lambda e: (len(e["picked_by"]), int(e.get("mentions") or 0)),
        reverse=True,
    )
    return ranked[:n]
