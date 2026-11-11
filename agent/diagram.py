"""Print the LangGraph pipeline as a Mermaid diagram and save it to docs/pipeline.mmd.

Usage: uv run python -m agent.diagram
Run it after changing the graph, then paste the output into the ```mermaid block in README.md.
"""
from pathlib import Path

from agent.graph import agent

OUT = Path(__file__).resolve().parent.parent / "docs" / "pipeline.mmd"

if __name__ == "__main__":
    diagram = agent.get_graph().draw_mermaid()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(diagram)
    print(diagram)
