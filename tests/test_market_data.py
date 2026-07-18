from unittest.mock import MagicMock, patch

from scanner.market_data import get_quote


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
