from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

from reddit import WSBPost

class State(TypedDict):
    posts: list[WSBPost]        # from reddit.py
    trending: list[dict]        # from apewisdom.py
    scores: list[dict]          # {"title", "label", "confidence"}
    newsletter: str
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int