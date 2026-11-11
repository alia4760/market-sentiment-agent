from typing_extensions import Annotated, TypedDict
import operator

# Process exit code per failing stage (0 = clean run). main.py exits with the first one.
EXIT_CODES = {
    "reddit": 2, "apewisdom": 3, "jev": 4, "db": 5, "tradestie": 6, "prices": 7,
    "premarket": 8, "earnings": 9, "tavily": 10, "llm": 11, "discord": 12, "pdf": 13,
}


class State(TypedDict):
    refresh: bool               # rebuild even if today's newsletter is stored
    collect_only: bool          # fetch and save data only: no Jev, no LLM, no newsletter, no Discord
    resend: bool                # send the report to Discord even if it was already sent today
    from_store: bool            # newsletter came from the database
    top_tickers: list[dict]     # full ApeWisdom top 50
    tradestie: list[dict]       # Tradestie top 50: ticker, sentiment, sentiment_score, no_of_comments
    trending: list[dict]        # top-10 candidates, merged from ApeWisdom and Tradestie
    prices: list[dict]          # recent daily close/volume for every ticker seen
    premarket: dict             # ticker -> latest extended-hours price vs last regular close
    earnings: dict              # ticker -> next earnings date
    news: dict                  # ticker -> today's headlines from Tavily (+ Jev catalyst)
    evidence: dict              # ticker -> {"source", "posts", "comments"} from Reddit
    sentiment: dict             # ticker -> Jev roll-up of the Reddit evidence
    brief: dict                 # LLM summary: overview, top_picks, per-ticker summaries
    newsletter: str
    pdf: bytes                  # the report rendered as a PDF
    errors: Annotated[list[dict], operator.add]   # {"stage", "message"}
