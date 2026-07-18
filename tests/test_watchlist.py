from unittest.mock import MagicMock, patch

from scanner.watchlist import get_watchlist


@patch("scanner.watchlist.create_client")
def test_get_watchlist_returns_rows(mock_create_client):
    mock_response = MagicMock()
    mock_response.data = [
        {
            "ticker": "AAPL",
            "owned": True,
            "shares": 10,
            "cost_basis": 150.0,
            "notes": "watching for earnings",
        },
        {
            "ticker": "TSLA",
            "owned": False,
            "shares": None,
            "cost_basis": None,
            "notes": None,
        },
    ]
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value = mock_response
    mock_create_client.return_value = mock_client

    result = get_watchlist("https://example.supabase.co", "service-key")

    mock_create_client.assert_called_once_with("https://example.supabase.co", "service-key")
    mock_client.table.assert_called_once_with("watchlist")
    assert len(result) == 2
    assert result[0]["ticker"] == "AAPL"
    assert result[1]["ticker"] == "TSLA"


@patch("scanner.watchlist.create_client")
def test_get_watchlist_returns_empty_list(mock_create_client):
    mock_response = MagicMock()
    mock_response.data = []
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value = mock_response
    mock_create_client.return_value = mock_client

    result = get_watchlist("https://example.supabase.co", "service-key")

    assert result == []
