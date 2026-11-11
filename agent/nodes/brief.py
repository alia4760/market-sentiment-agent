import json
import logging
import os
from datetime import datetime, timezone

from typing import Literal

from pydantic import BaseModel

from agent.errors import record_error
from agent.facts import build_facts, market_context
from agent.prompts import SYSTEM_PROMPT
from agent.state import State

log = logging.getLogger(__name__)


class Pick(BaseModel):
    ticker: str
    direction: Literal["long", "short", "watch", "avoid"]
    reason: str


class TickerBrief(BaseModel):
    ticker: str
    stance: Literal["bullish", "bearish", "neutral", "avoid"]
    horizon: Literal["day trade", "swing", "watch only"]
    summary: str


class Brief(BaseModel):
    overview: str
    top_picks: list[Pick]
    tickers: list[TickerBrief]


def brief(state: State) -> dict:
    """One LLM call turns the facts into an overview, top picks and a short summary per ticker.

    The model is chosen with the BRIEF_MODEL env var, for example "openai:<model>" or
    "anthropic:<model>". BRIEF_EFFORT sets the reasoning effort (default medium).
    If BRIEF_MODEL is not set the step is skipped and the report is template-only.
    """
    if state.get("collect_only"):
        log.info("LLM: summary skipped (collect-only run)")
        return {}
    model = os.environ.get("BRIEF_MODEL")
    if not model:
        log.info("LLM: BRIEF_MODEL is not set; skipping the summary")
        return {}
    facts = build_facts(state)
    if not facts:
        return {}
    try:
        from langchain.chat_models import init_chat_model

        effort = os.environ.get("BRIEF_EFFORT", "medium")
        llm = init_chat_model(model, reasoning_effort=effort).with_structured_output(Brief, include_raw=True)
        payload = {
            "date": datetime.now(timezone.utc).strftime("%A %B %d, %Y"),
            "market": market_context(state),
            "tickers": facts,
        }
        log.info("LLM: writing the brief for %d tickers with %s (reasoning effort %s)", len(facts), model, effort)
        result = llm.invoke([("system", SYSTEM_PROMPT), ("human", json.dumps(payload, default=str))])
        usage = getattr(result["raw"], "usage_metadata", None) or {}
        log.info(
            "LLM: tokens in=%s out=%s (reasoning=%s)",
            usage.get("input_tokens"), usage.get("output_tokens"),
            (usage.get("output_token_details") or {}).get("reasoning"),
        )
        if result["parsed"] is None:
            raise RuntimeError(f"LLM output did not match the brief format: {result['parsing_error']}")
        return {"brief": result["parsed"].model_dump()}
    except Exception as e:
        return {"errors": [record_error("llm", e)]}
