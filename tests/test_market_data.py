from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from scanner.market_data import get_quote, get_company_news, get_general_news


@patch("scanner.market_data.requests.get")
def test_get_quote_computes_pct_change(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"c": 110.0, "pc": 100.0}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_quote("AAPL", "finnhub-key")

    assert result["current_price"] == 110.0
    assert result["previous_close"] == 100.0
    assert result["pct_change"] == 10.0
    mock_get.assert_called_once_with(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": "AAPL", "token": "finnhub-key"},
        timeout=10,
    )


@patch("scanner.market_data.requests.get")
def test_get_quote_handles_negative_change(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"c": 90.0, "pc": 100.0}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_quote("TSLA", "finnhub-key")

    assert result["pct_change"] == -10.0


@patch("scanner.market_data.requests.get")
def test_get_quote_handles_zero_previous_close(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"c": 5.0, "pc": 0.0}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_quote("NEWCO", "finnhub-key")

    assert result["pct_change"] == 0.0


@patch("scanner.market_data.requests.get")
def test_get_company_news_returns_top_headlines(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"headline": "Headline 1", "url": "https://example.com/1"},
        {"headline": "Headline 2", "url": "https://example.com/2"},
        {"headline": "Headline 3", "url": "https://example.com/3"},
        {"headline": "Headline 4", "url": "https://example.com/4"},
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_company_news("AAPL", "finnhub-key", limit=3)

    assert len(result) == 3
    assert result[0] == {"headline": "Headline 1", "url": "https://example.com/1"}
    called_args, called_kwargs = mock_get.call_args
    assert called_args[0] == "https://finnhub.io/api/v1/company-news"
    assert called_kwargs["params"]["symbol"] == "AAPL"
    assert called_kwargs["params"]["token"] == "finnhub-key"
    assert "from" in called_kwargs["params"]
    assert "to" in called_kwargs["params"]


@patch("scanner.market_data.requests.get")
def test_get_general_news_returns_top_headlines(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"headline": "Market Headline", "url": "https://example.com/m"},
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_general_news("finnhub-key", limit=8)

    assert result == [{"headline": "Market Headline", "url": "https://example.com/m"}]
    mock_get.assert_called_once_with(
        "https://finnhub.io/api/v1/news",
        params={"category": "general", "token": "finnhub-key"},
        timeout=10,
    )
