"""Print the LangGraph pipeline as a Mermaid diagram.

Usage: uv run python -m agent.diagram
Paste the output into the ```mermaid block in README.md after changing the graph.
"""
from agent.graph import agent

if __name__ == "__main__":
    print(agent.get_graph().draw_mermaid())
