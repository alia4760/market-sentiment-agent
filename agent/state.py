from langchain.messages import AnyMessage
from typing_extensions import Annotated, TypedDict
import operator

from sources.reddit import WSBPost

# Process exit code per failing stage (0 = clean run). main.py exits with the first one.
EXIT_CODES = {"reddit": 2, "apewisdom": 3, "jev": 4, "db": 5, "tradestie": 6, "prices": 7, "premarket": 8, "earnings": 9, "tavily": 10}


class State(TypedDict):
    refresh: bool               # rebuild even if today's newsletter is stored
    collect_only: bool          # fetch and save data only; no Jev scoring, no newsletter stored
    from_store: bool            # newsletter came from the database
    posts: list[WSBPost]        # from reddit.py
    top_tickers: list[dict]     # full ApeWisdom top 50
    trending: list[dict]        # top candidates, merged from ApeWisdom and Tradestie
    tradestie: list[dict]       # Tradestie top 50: ticker, sentiment, sentiment_score, no_of_comments
    prices: list[dict]          # recent daily close/volume for every ticker seen
    premarket: dict             # ticker -> latest extended-hours price vs last regular close
    earnings: dict              # ticker -> next earnings date
    news: dict                  # ticker -> today's headlines from Tavily
    scores: list[dict]          # {"title", "url", "label", "confidence"}
    newsletter: str
    errors: Annotated[list[dict], operator.add]   # {"stage", "message"}
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
