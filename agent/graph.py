from langgraph.graph import END, START, StateGraph

from agent.nodes.fetch import fetch
from agent.nodes.fetch_earnings import fetch_earnings
from agent.nodes.fetch_prices import fetch_prices
from agent.nodes.load_stored import after_load, load_stored
from agent.nodes.rank import rank
from agent.nodes.research import research
from agent.nodes.save import save
from agent.nodes.score import score
from agent.nodes.summarize import summarize
from agent.state import State

graph = StateGraph(State)
graph.add_node("load_stored", load_stored)
graph.add_node("fetch", fetch)
graph.add_node("rank", rank)
graph.add_node("fetch_prices", fetch_prices)
graph.add_node("fetch_earnings", fetch_earnings)
graph.add_node("research", research)
graph.add_node("score", score)
graph.add_node("summarize", summarize)
graph.add_node("save", save)
graph.add_edge(START, "load_stored")
graph.add_conditional_edges("load_stored", after_load, ["fetch", END])
graph.add_edge("fetch", "rank")
graph.add_edge("rank", "fetch_prices")
graph.add_edge("fetch_prices", "fetch_earnings")
graph.add_edge("fetch_earnings", "research")
graph.add_edge("research", "score")
graph.add_edge("score", "summarize")
graph.add_edge("summarize", "save")
graph.add_edge("save", END)

agent = graph.compile()
