"""Print the LangGraph pipeline as a Mermaid diagram and save it to docs/pipeline.mmd.

Usage: uv run python -m docs.diagram
Run it after changing the graph, then paste the output into the ```mermaid block in README.md.
"""
from pathlib import Path

from agent.graph import agent

OUT = Path(__file__).resolve().parent / "pipeline.mmd"

# LangGraph's default colours leave light text on a light fill in GitHub's dark theme.
# Give every box an explicit fill, border and dark text so it reads in light and dark mode.
STYLES = (
    "\tclassDef default fill:#e8eefc,stroke:#4a6fa5,color:#111827,line-height:1.2\n"
    "\tclassDef first fill:#d1fae5,stroke:#2f7d5b,color:#111827\n"
    "\tclassDef last fill:#d1fae5,stroke:#2f7d5b,color:#111827\n"
)


def build() -> str:
    lines = agent.get_graph().draw_mermaid().splitlines(keepends=True)
    return "".join(l for l in lines if not l.strip().startswith("classDef")).rstrip("\n") + "\n" + STYLES


if __name__ == "__main__":
    diagram = build()
    OUT.write_text(diagram)
    print(diagram)
