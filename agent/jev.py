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


def classify_sentiment(texts: list[str]) -> list[dict]:
    """Label each text bullish/bearish/neutral with Jev. Returns {"label", "confidence"} per text."""
    classifier = TypeSafeClassifier(
        model="jev-latest", api_key=os.environ["JEV_API_KEY"]
    )
    requests = [
        {"state": text, "questions": {"sentiment": SENTIMENT_QUESTION}}
        for text in texts
    ]
    answers = classifier.batch(requests)
    return [
        {
            "label": answer.choices["sentiment"].choice,
            "confidence": answer.choices["sentiment"].confidence,
        }
        for answer in answers
    ]
