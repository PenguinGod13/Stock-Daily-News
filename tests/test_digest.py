from unittest.mock import MagicMock, patch

from scanner.digest import build_digest, build_fallback_digest

TICKER_RECORDS = [
    {
        "ticker": "AAPL",
        "current_price": 110.0,
        "pct_change": 10.0,
        "is_mover": True,
        "owned": True,
        "shares": 10,
        "cost_basis": 100.0,
        "unrealized_pl": 100.0,
        "notes": None,
        "top_headlines": [{"headline": "AAPL surges", "url": "https://example.com/1"}],
    },
    {
        "ticker": "MSFT",
        "current_price": 300.0,
        "pct_change": 0.5,
        "is_mover": False,
        "owned": False,
        "shares": None,
        "cost_basis": None,
        "unrealized_pl": None,
        "notes": None,
        "top_headlines": [],
    },
]
MARKET_TRENDS = [{"title": "AI chip demand surges", "url": "https://example.com/a", "content": "..."}]
MARKET_MOVERS = [{"title": "NVDA +8% on earnings beat", "url": "https://example.com/n", "content": "..."}]


@patch("scanner.digest.requests.post")
def test_build_digest_returns_ai_content_on_success(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"message": {"content": "# TL;DR\nMarkets were mixed today."}}
    mock_post.return_value = mock_response

    result = build_digest("ollama-key", TICKER_RECORDS, MARKET_TRENDS)

    assert result == "# TL;DR\nMarkets were mixed today."
    called_args, called_kwargs = mock_post.call_args
    assert called_args[0] == "https://ollama.com/api/chat"
    assert called_kwargs["headers"]["Authorization"] == "Bearer ollama-key"
    assert called_kwargs["json"]["model"] == "gpt-oss:120b"
    assert called_kwargs["json"]["stream"] is False


@patch("scanner.digest.requests.post")
def test_build_digest_retries_once_then_falls_back(mock_post):
    mock_post.side_effect = Exception("network error")

    result = build_digest("ollama-key", TICKER_RECORDS, MARKET_TRENDS)

    assert mock_post.call_count == 2
    assert "AAPL" in result
    assert "fallback" in result.lower()


def test_build_fallback_digest_lists_movers_and_rest():
    result = build_fallback_digest(TICKER_RECORDS, MARKET_TRENDS, MARKET_MOVERS)

    assert "AAPL" in result
    assert "10.00%" in result
    assert "100.00" in result
    assert "MSFT" in result
    assert "AI chip demand surges" in result
    assert "AAPL surges" in result
    assert "NVDA +8%" in result


def test_build_fallback_digest_handles_no_movers():
    no_movers = [dict(r, is_mover=False) for r in TICKER_RECORDS]

    result = build_fallback_digest(no_movers, MARKET_TRENDS)

    assert "No tickers moved beyond the threshold" in result
