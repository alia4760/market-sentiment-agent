from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
import operator

from reddit import WSBPost, get_wsb_top_posts
from apewisdom import get_wsb_trending, pick_candidates
from jev import classify_sentiment


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
        "trending": pick_candidates(get_wsb_trending(limit=50)),
    }


def _post_text(post: WSBPost) -> str:
    return f"{post['title']}\n\n{post['body'][:1500]}".strip()


def score(state: State) -> dict:
    results = classify_sentiment([_post_text(post) for post in state["posts"]])
    scores = [
        {"title": post["title"], **result}
        for post, result in zip(state["posts"], results)
    ]
    return {"scores": scores}


def summarize(state: State) -> dict:
    lines = ["=== Market Sentiment Newsletter ===", "", "Trending tickers:"]
    for stock in state["trending"]:
        picked = "+".join(stock["picked_by"])
        lines.append(
            f"  {stock['ticker']}: {stock['mentions']} mentions "
            f"(was {stock.get('mentions_24h_ago', 'N/A')}) [{picked}]"
        )

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