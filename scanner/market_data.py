import requests
from datetime import date, timedelta

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_quote(ticker, api_key):
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/quote",
        params={"symbol": ticker, "token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    current_price = data["c"]
    previous_close = data["pc"]
    pct_change = (
        ((current_price - previous_close) / previous_close) * 100
        if previous_close
        else 0.0
    )
    return {
        "current_price": current_price,
        "previous_close": previous_close,
        "pct_change": pct_change,
    }


def get_company_news(ticker, api_key, days=2, limit=3):
    to_date = date.today()
    from_date = to_date - timedelta(days=days)
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/company-news",
        params={
            "symbol": ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": api_key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json()
    return [{"headline": a["headline"], "url": a["url"]} for a in articles[:limit]]


def get_general_news(api_key, limit=8):
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/news",
        params={"category": "general", "token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json()
    return [{"headline": a["headline"], "url": a["url"]} for a in articles[:limit]]
