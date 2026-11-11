import pytest

from sources.reddit_search import mentions_ticker

CASES = [
    # (text, ticker, company name, expected)
    ("AI is going to eat the world", "AI", "C3.ai, Inc.", False),
    ("I'm going ON a trip next week", "ON", "ON Semiconductor Corporation", False),
    ("IT guy here, my day job is boring", "IT", "Gartner, Inc.", False),
    ("do it NOW, I am tired of waiting", "NOW", "ServiceNow, Inc.", False),
    ("buy NOW before it moons", "NOW", "ServiceNow, Inc.", True),
    ("$AI earnings Thursday, loading up", "AI", "C3.ai, Inc.", True),
    ("ServiceNow beat, NOW up 8%", "NOW", "ServiceNow, Inc.", True),
    ("loaded NOW calls for Friday", "NOW", "ServiceNow, Inc.", True),
    ("NVDA to the moon", "NVDA", "NVIDIA Corporation", True),
    ("nvda to the moon", "NVDA", "NVIDIA Corporation", True),
    ("NVDAX is something else", "NVDA", "NVIDIA Corporation", False),
    ("F earnings tomorrow", "F", "Ford Motor Company", True),
    ("F you all, I'm out", "F", "Ford Motor Company", False),
]


@pytest.mark.parametrize("text,ticker,name,expected", CASES)
def test_mentions_ticker(text, ticker, name, expected):
    assert mentions_ticker(text, ticker, name) is expected
