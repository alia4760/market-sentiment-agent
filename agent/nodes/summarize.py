from datetime import datetime, timezone

from agent.facts import build_facts, market_context
from agent.state import State


def _ticker_block(f: dict, brief: dict | None) -> list[str]:
    attention = f"**{f['ticker']}**"
    if f["name"]:
        attention += f" ({f['name']})"
    if f["mentions"] is not None:
        attention += f" · {f['mentions']} mentions (was {f['mentions_24h_ago'] if f['mentions_24h_ago'] is not None else 'n/a'})"
    if f["tradestie"]:
        attention += f" · Tradestie {f['tradestie']['label']} {f['tradestie']['score']:+.2f}"
    lines = [attention]

    price = []
    if f["prev_day_pct"] is not None:
        price.append(f"prev day {f['prev_day_pct']:+.1f}%")
    if f["premarket"]:
        label = {"pre": "pre-market", "post": "after-hours", "regular": "live"}[f["premarket"]["session"]]
        price.append(f"{label} {f['premarket']['pct']:+.1f}%")
    if f["earnings"]:
        price.append(f"earnings {f['earnings']}")
    if price:
        lines.append("  " + " · ".join(price))

    r = f["reddit"]
    if r and r.get("n"):
        thin = ", thin" if r.get("thin") else ""
        lines.append(
            f"  Reddit ({r['source']}{thin}): {r['bullish']} bullish / {r['bearish']} bearish / "
            f"{r['neutral']} neutral (net {r['net']:+.2f})"
        )
    elif r:
        lines.append("  Reddit: no recent posts found")

    for h in f["headlines"][:2]:
        tag = f"[{h['catalyst']}] " if h.get("catalyst") else ""
        title = f"[{h['title']}]({h['url']})" if h.get("url") else h["title"]
        lines.append(f"  • {tag}{title}")
    if brief:
        lines.append(f"  **Lean: {brief['stance']} · {brief['horizon']}.** {brief['summary']}")
    return lines


def summarize(state: State) -> dict:
    """Fill the report template from the facts, plus the LLM brief when there is one."""
    facts = build_facts(state)
    brief = state.get("brief") or {}
    by_ticker = {t["ticker"]: t for t in brief.get("tickers", [])}
    title = datetime.now(timezone.utc).strftime("%A %B %d")
    lines = [f"**Market Sentiment Brief · {title}**", ""]

    market = market_context(state)
    if market:
        label = {"pre": "pre-market", "post": "after-hours", "regular": "live"}
        lines.append("Market: " + ", ".join(f"{t} {m['pct']:+.1f}% {label[m['session']]}" for t, m in market.items()))
        lines.append("")
    if brief.get("overview"):
        lines += [brief["overview"], ""]
    if brief.get("top_picks"):
        lines.append("**Worth a look**")
        lines += [f"{i}. **{p['ticker']}** ({p['direction']}): {p['reason']}" for i, p in enumerate(brief["top_picks"], 1)]
        lines.append("")

    if facts:
        lines.append("**Candidates**" if brief else "**Top candidates**")
        for f in facts:
            lines += _ticker_block(f, by_ticker.get(f["ticker"])) + [""]
    else:
        lines.append("(no candidates today: the ticker sources were unavailable)")

    if brief:
        lines.append("_Automated analysis from public data; verify before trading._")
    return {"newsletter": "\n".join(lines).rstrip() + "\n"}
