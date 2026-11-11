import os

from dotenv import load_dotenv
from langchain_typesafe import Choice, TypeSafeClassifier

load_dotenv()

SENTIMENT_QUESTION = Choice(
    instructions="What is the sentiment of this r/wallstreetbets post toward the stocks it discusses?",
    criteria={
        "bullish": "Expects or hopes prices will rise; optimistic, buying, long positions.",
        "bearish": "Expects prices to fall; pessimistic, selling, short positions.",
        "neutral": "No clear directional view, news-only, or off-topic.",
    },
)

CATALYST_QUESTION = Choice(
    instructions="What is the main catalyst behind this stock news headline?",
    criteria={
        "earnings": "Quarterly results, guidance, or an earnings preview or reaction.",
        "analyst": "An analyst upgrade, downgrade, price target change, or rating.",
        "deal": "A product launch, partnership, contract, acquisition, or funding or IPO event.",
        "legal": "A lawsuit, investigation, regulation, or government action.",
        "macro": "Market-wide or sector-wide moves, the economy, rates, or politics.",
        "price-action": "Only describes the price move or trading activity with no stated cause.",
        "other": "Anything else.",
    },
)


def _classify(texts: list[str], key: str, question: Choice) -> list[dict]:
    classifier = TypeSafeClassifier(model="jev-latest", api_key=os.environ["JEV_API_KEY"])
    answers = classifier.batch(
        [{"state": text, "questions": {key: question}} for text in texts]
    )
    return [
        {"label": a.choices[key].choice, "confidence": a.choices[key].confidence}
        for a in answers
    ]


def classify_sentiment(texts: list[str]) -> list[dict]:
    """Label each text bullish/bearish/neutral with Jev. Returns {"label", "confidence"} per text."""
    return _classify(texts, "sentiment", SENTIMENT_QUESTION)


def classify_catalyst(headlines: list[str]) -> list[dict]:
    """Label each headline with its main catalyst. Returns {"label", "confidence"} per headline."""
    return _classify(headlines, "catalyst", CATALYST_QUESTION)
