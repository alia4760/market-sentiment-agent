from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import operator

from reddit import WSBPost, get_wsb_top_posts
from apewisdom import get_wsb_trending

class State(TypedDict):
    posts: list[WSBPost]        # from reddit.py
    trending: list[dict]        # from apewisdom.py
    scores: list[dict]          # {"title", "label", "confidence"}
    newsletter: str
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


def fetch(state: State) -> dict:
    return {
        "posts": get_wsb_top_posts(),
        "trending": get_wsb_trending(),
    }


def score(state: State) -> dict:
    scores = [
        {"title": post["title"], "label": "neutral", "confidence": 0.0}
        for post in state["posts"]
    ]
    return {"scores": scores}


def summarize(state: State) -> dict:
    lines = ["=== Market Sentiment Newsletter ===", "", "Trending tickers:"]
    for stock in state["trending"]:
        lines.append(f"  {stock['ticker']}: {stock['mentions']} mentions")

    lines.append("")
    lines.append("WSB post sentiment:")
    for item in state["scores"]:
        lines.append(f"  [{item['label']} ({item['confidence']:.2f})] {item['title']}")

    return {"newsletter": "\n".join(lines)}


graph = StateGraph(State)
graph.add_node("fetch", fetch)
graph.add_node("score", score)
graph.add_node("summarize", summarize)
graph.add_edge(START, "fetch")
graph.add_edge("fetch", "score")
graph.add_edge("score", "summarize")
graph.add_edge("summarize", END)

agent = graph.compile()