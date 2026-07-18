from unittest.mock import MagicMock, patch

from scanner.watchlist import get_watchlist

JWT_LIKE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.abc123signature"
NEW_FORMAT_KEY = "non-jwt-style-test-api-key-without-dots"


@patch("scanner.watchlist.requests.get")
def test_get_watchlist_returns_rows(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
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
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_watchlist("https://example.supabase.co", JWT_LIKE_KEY)

    assert len(result) == 2
    assert result[0]["ticker"] == "AAPL"
    assert result[1]["ticker"] == "TSLA"
    called_args, called_kwargs = mock_get.call_args
    assert called_args[0] == "https://example.supabase.co/rest/v1/watchlist"
    assert called_kwargs["params"] == {"select": "*"}
    assert called_kwargs["headers"]["apikey"] == JWT_LIKE_KEY


@patch("scanner.watchlist.requests.get")
def test_get_watchlist_returns_empty_list(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_watchlist("https://example.supabase.co", JWT_LIKE_KEY)

    assert result == []


@patch("scanner.watchlist.requests.get")
def test_get_watchlist_sends_bearer_header_for_jwt_style_keys(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    get_watchlist("https://example.supabase.co", JWT_LIKE_KEY)

    _, called_kwargs = mock_get.call_args
    assert called_kwargs["headers"]["Authorization"] == f"Bearer {JWT_LIKE_KEY}"


@patch("scanner.watchlist.requests.get")
def test_get_watchlist_omits_bearer_header_for_new_format_keys(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    get_watchlist("https://example.supabase.co", NEW_FORMAT_KEY)

    _, called_kwargs = mock_get.call_args
    assert called_kwargs["headers"]["apikey"] == NEW_FORMAT_KEY
    assert "Authorization" not in called_kwargs["headers"]
