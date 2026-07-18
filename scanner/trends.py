import requests

from scanner.market_data import get_general_news

OLLAMA_WEB_SEARCH_URL = "https://ollama.com/api/web_search"


def get_market_trends(ollama_api_key, finnhub_api_key):
    try:
        resp = requests.post(
            OLLAMA_WEB_SEARCH_URL,
            headers={"Authorization": f"Bearer {ollama_api_key}"},
            json={"query": "stock market trends and hot sectors today", "max_results": 8},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
            for r in data.get("results", [])
        ]
    except Exception:
        try:
            articles = get_general_news(finnhub_api_key)
            return [{"title": a["headline"], "url": a["url"], "content": ""} for a in articles]
        except Exception:
            return []
