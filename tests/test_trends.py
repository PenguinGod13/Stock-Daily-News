from unittest.mock import MagicMock, patch

from scanner.trends import get_market_trends


@patch("scanner.trends.requests.post")
def test_get_market_trends_uses_web_search_results(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "results": [
            {"title": "AI chip demand surges", "url": "https://example.com/a", "content": "..."},
            {"title": "Biotech rally continues", "url": "https://example.com/b", "content": "..."},
        ]
    }
    mock_post.return_value = mock_response

    result = get_market_trends("ollama-key", "finnhub-key")

    assert len(result) == 2
    assert result[0] == {
        "title": "AI chip demand surges",
        "url": "https://example.com/a",
        "content": "...",
    }
    mock_post.assert_called_once()
    called_args, called_kwargs = mock_post.call_args
    assert called_args[0] == "https://ollama.com/api/web_search"
    assert called_kwargs["headers"]["Authorization"] == "Bearer ollama-key"
    assert "query" in called_kwargs["json"]


@patch("scanner.trends.get_general_news")
@patch("scanner.trends.requests.post")
def test_get_market_trends_falls_back_to_finnhub_on_error(mock_post, mock_get_general_news):
    mock_post.side_effect = Exception("network error")
    mock_get_general_news.return_value = [
        {"headline": "Market steady", "url": "https://example.com/m"},
    ]

    result = get_market_trends("ollama-key", "finnhub-key")

    assert result == [{"title": "Market steady", "url": "https://example.com/m", "content": ""}]
    mock_get_general_news.assert_called_once_with("finnhub-key")


@patch("scanner.trends.get_general_news")
@patch("scanner.trends.requests.post")
def test_get_market_trends_returns_empty_list_when_both_sources_fail(mock_post, mock_get_general_news):
    mock_post.side_effect = Exception("network error")
    mock_get_general_news.side_effect = Exception("finnhub down")

    result = get_market_trends("ollama-key", "finnhub-key")

    assert result == []
