import requests

from scanner.market_data import get_general_news

OLLAMA_WEB_SEARCH_URL = "https://ollama.com/api/web_search"


def _web_search(ollama_api_key, query, max_results=8):
    resp = requests.post(
        OLLAMA_WEB_SEARCH_URL,
        headers={"Authorization": f"Bearer {ollama_api_key}"},
        json={"query": query, "max_results": max_results},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
        for r in data.get("results", [])
    ]


def get_market_trends(ollama_api_key, finnhub_api_key):
    try:
        return _web_search(ollama_api_key, "stock market trends and hot sectors today")
    except Exception:
        try:
            articles = get_general_news(finnhub_api_key)
            return [{"title": a["headline"], "url": a["url"], "content": ""} for a in articles]
        except Exception:
            return []


def get_market_movers(ollama_api_key, finnhub_api_key):
    """Fetch biggest stock movers (gainers + losers) outside the user's watchlist."""
    try:
        return _web_search(
            ollama_api_key,
            "biggest stock market movers today top gainers losers percentage change",
            max_results=8,
        )
    except Exception:
        try:
            articles = get_general_news(finnhub_api_key)
            return [{"title": a["headline"], "url": a["url"], "content": ""} for a in articles]
        except Exception:
            return []
