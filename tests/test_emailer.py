from unittest.mock import MagicMock, patch

from scanner.emailer import markdown_to_html, render_ticker_table, render_digest_email, send_email, send_debug_email

MOVER_RECORD = {
    "ticker": "AAPL", "current_price": 210.50, "pct_change": 4.2,
    "is_mover": True, "owned": True, "shares": 10, "cost_basis": 180.0,
    "unrealized_pl": 305.0, "notes": None, "top_headlines": [],
}
FLAT_RECORD = {
    "ticker": "MSFT", "current_price": 420.00, "pct_change": -0.5,
    "is_mover": False, "owned": False, "shares": None, "cost_basis": None,
    "unrealized_pl": None, "notes": None, "top_headlines": [],
}


def test_render_ticker_table_shows_green_for_gain():
    result = render_ticker_table([MOVER_RECORD])
    assert "AAPL" in result
    assert "+4.20%" in result
    assert "#0a7d34" in result  # green colour for positive change
    assert "MOVER" in result
    assert "+$305.00" in result


def test_render_ticker_table_shows_red_for_loss():
    result = render_ticker_table([FLAT_RECORD])
    assert "MSFT" in result
    assert "-0.50%" in result
    assert "#c0362c" in result  # red colour for negative change
    assert "MOVER" not in result
    assert "&mdash;" in result  # no P&L for non-owned


def test_render_ticker_table_empty_returns_empty_string():
    assert render_ticker_table([]) == ""


def test_render_digest_email_contains_table_and_narrative():
    result = render_digest_email("# TL;DR\nMarkets were up.", [MOVER_RECORD], "Mon Jul 21")
    assert "AAPL" in result
    assert "TL;DR" in result
    assert "Mon Jul 21" in result
    assert "<!DOCTYPE html>" in result
    assert 'name="viewport"' in result  # mobile meta tag



    result = markdown_to_html("# Hello\n\nWorld")

    assert "<h1>Hello</h1>" in result
    assert "<p>World</p>" in result


@patch("scanner.emailer.smtplib.SMTP_SSL")
def test_send_email_logs_in_and_sends(mock_smtp_ssl):
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    send_email("me@gmail.com", "app-password", "me@gmail.com", "Subject", "<p>Body</p>")

    mock_smtp_ssl.assert_called_once_with("smtp.gmail.com", 465)
    mock_server.login.assert_called_once_with("me@gmail.com", "app-password")
    assert mock_server.sendmail.call_count == 1
    args, kwargs = mock_server.sendmail.call_args
    assert args[0] == "me@gmail.com"
    assert args[1] == ["me@gmail.com"]
    assert "Subject" in args[2]
    assert "Body" in args[2]


@patch("scanner.emailer.smtplib.SMTP_SSL")
def test_send_email_supports_multiple_comma_separated_recipients(mock_smtp_ssl):
    mock_server = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = mock_server

    send_email("me@gmail.com", "app-password", "a@example.com, b@example.com", "Subject", "<p>Body</p>")

    args, kwargs = mock_server.sendmail.call_args
    assert args[1] == ["a@example.com", "b@example.com"]
    assert "a@example.com, b@example.com" in args[2]


@patch("scanner.emailer.send_email")
def test_send_debug_email_includes_all_errors(mock_send_email):
    send_debug_email("me@gmail.com", "app-password", "me@gmail.com", ["error one", "error two"])

    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    assert args[0] == "me@gmail.com"
    assert args[1] == "app-password"
    assert args[2] == "me@gmail.com"
    assert "Debug" in args[3]
    assert "error one" in args[4]
    assert "error two" in args[4]


@patch("scanner.emailer.send_email")
def test_send_debug_email_escapes_html_in_errors(mock_send_email):
    send_debug_email("me@gmail.com", "app-password", "me@gmail.com", ["error with <script>alert('xss')</script>"])

    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    body = args[4]
    # Check that the dangerous HTML is escaped, not rendered as tags
    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert "alert" in body  # The content is there, just escaped
