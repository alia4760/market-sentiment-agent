from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_typesafe import Choice, TypeSafeClassifier
from dotenv import load_dotenv
import operator
import os

from reddit import WSBPost, get_wsb_top_posts
from apewisdom import get_wsb_trending

load_dotenv()

SENTIMENT_QUESTION = Choice(
    instructions="What is the sentiment of this r/wallstreetbets post toward the stocks it discusses?",
    criteria={
        "bullish": "Expects or hopes prices will rise; optimistic, buying, long positions.",
        "bearish": "Expects prices to fall; pessimistic, selling, short positions.",
        "neutral": "No clear directional view, news-only, or off-topic.",
    },
)


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


def _post_text(post: WSBPost) -> str:
    return f"{post['title']}\n\n{post['body'][:1500]}".strip()


def score(state: State) -> dict:
    classifier = TypeSafeClassifier(
        model="jev-latest", api_key=os.environ["JEV_API_KEY"]
    )
    requests = [
        {"state": _post_text(post), "questions": {"sentiment": SENTIMENT_QUESTION}}
        for post in state["posts"]
    ]
    answers = classifier.batch(requests)
    scores = [
        {
            "title": post["title"],
            "label": answer.choices["sentiment"].choice,
            "confidence": answer.choices["sentiment"].confidence,
        }
        for post, answer in zip(state["posts"], answers)
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