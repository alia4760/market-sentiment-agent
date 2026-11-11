from langgraph.graph import END, START, StateGraph

from agent.nodes.brief import brief
from agent.nodes.classify_news import classify_news
from agent.nodes.fetch import fetch
from agent.nodes.fetch_earnings import fetch_earnings
from agent.nodes.fetch_prices import fetch_prices
from agent.nodes.load_stored import after_load, load_stored
from agent.nodes.notify import notify
from agent.nodes.rank import rank
from agent.nodes.render_pdf import render_pdf
from agent.nodes.reddit_evidence import reddit_evidence
from agent.nodes.research import research
from agent.nodes.save import save
from agent.nodes.score_evidence import score_evidence
from agent.nodes.summarize import summarize
from agent.state import State

graph = StateGraph(State)
graph.add_node("load_stored", load_stored)
graph.add_node("fetch", fetch)
graph.add_node("rank", rank)
graph.add_node("fetch_prices", fetch_prices)
graph.add_node("fetch_earnings", fetch_earnings)
graph.add_node("research", research)
graph.add_node("classify_news", classify_news)
graph.add_node("reddit_evidence", reddit_evidence)
graph.add_node("score_evidence", score_evidence)
graph.add_node("brief", brief)
graph.add_node("summarize", summarize)
graph.add_node("render_pdf", render_pdf)
graph.add_node("save", save)
graph.add_node("notify", notify)

graph.add_edge(START, "load_stored")
graph.add_conditional_edges("load_stored", after_load, ["fetch", "notify"])
graph.add_edge("fetch", "rank")
graph.add_edge("rank", "fetch_prices")
graph.add_edge("fetch_prices", "fetch_earnings")
graph.add_edge("fetch_earnings", "research")
graph.add_edge("research", "classify_news")
graph.add_edge("classify_news", "reddit_evidence")
graph.add_edge("reddit_evidence", "score_evidence")
graph.add_edge("score_evidence", "brief")
graph.add_edge("brief", "summarize")
graph.add_edge("summarize", "render_pdf")
graph.add_edge("render_pdf", "save")
graph.add_edge("save", "notify")
graph.add_edge("notify", END)

agent = graph.compile()
