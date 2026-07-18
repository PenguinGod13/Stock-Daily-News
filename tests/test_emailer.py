from unittest.mock import MagicMock, patch

from scanner.emailer import markdown_to_html, send_email, send_debug_email


def test_markdown_to_html_converts_heading():
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
