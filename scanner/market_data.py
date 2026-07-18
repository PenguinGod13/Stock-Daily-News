import requests

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
