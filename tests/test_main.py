from unittest.mock import patch

from scanner.main import run

BASE_CONFIG = {
    "ollama_api_key": "ollama-key",
    "finnhub_api_key": "finnhub-key",
    "supabase_url": "https://example.supabase.co",
    "supabase_service_key": "service-key",
    "gmail_address": "me@gmail.com",
    "gmail_app_password": "app-password",
    "recipient_email": "me@gmail.com",
    "dry_run": False,
    "debug_emails": True,
}

WATCHLIST = [
    {"ticker": "AAPL", "owned": True, "shares": 10, "cost_basis": 100.0, "notes": None},
]


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", return_value={"current_price": 110.0, "previous_close": 100.0, "pct_change": 10.0})
@patch("scanner.main.get_company_news", return_value=[])
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
@patch("scanner.main.send_debug_email")
def test_run_sends_email_on_success(
    mock_send_debug, mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_news, mock_get_quote, mock_get_watchlist, mock_is_run_window,
):
    run(config=dict(BASE_CONFIG))

    mock_send_email.assert_called_once()
    mock_send_debug.assert_not_called()


@patch("scanner.main.is_run_window", return_value=False)
@patch("scanner.main.get_watchlist")
@patch("scanner.main.send_email")
def test_run_skips_outside_window_unless_forced(mock_send_email, mock_get_watchlist, mock_is_run_window):
    run(config=dict(BASE_CONFIG))

    mock_get_watchlist.assert_not_called()
    mock_send_email.assert_not_called()


@patch("scanner.main.is_run_window", return_value=False)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", return_value={"current_price": 110.0, "previous_close": 100.0, "pct_change": 10.0})
@patch("scanner.main.get_company_news", return_value=[])
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
def test_run_force_bypasses_time_gate(
    mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_news, mock_get_quote, mock_get_watchlist, mock_is_run_window,
):
    run(config=dict(BASE_CONFIG), force=True)

    mock_send_email.assert_called_once()


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=[])
@patch("scanner.main.send_email")
def test_run_skips_empty_watchlist(mock_send_email, mock_get_watchlist, mock_is_run_window):
    run(config=dict(BASE_CONFIG))

    mock_send_email.assert_not_called()


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", side_effect=Exception("finnhub down"))
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
@patch("scanner.main.send_debug_email")
def test_run_collects_ticker_errors_and_sends_debug_email(
    mock_send_debug, mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_quote, mock_get_watchlist, mock_is_run_window,
):
    run(config=dict(BASE_CONFIG))

    mock_send_email.assert_called_once()
    mock_send_debug.assert_called_once()
    debug_args, _ = mock_send_debug.call_args
    assert any("AAPL" in e for e in debug_args[3])


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", return_value={"current_price": 110.0, "previous_close": 100.0, "pct_change": 10.0})
@patch("scanner.main.get_company_news", return_value=[])
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
def test_run_dry_run_does_not_send(
    mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_news, mock_get_quote, mock_get_watchlist, mock_is_run_window,
    capsys,
):
    config = dict(BASE_CONFIG)
    config["dry_run"] = True

    run(config=config)

    mock_send_email.assert_not_called()
    captured = capsys.readouterr()
    assert "TL;DR" in captured.out


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", side_effect=Exception("finnhub down"))
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
@patch("scanner.main.send_debug_email")
def test_run_does_not_send_debug_email_when_debug_emails_false(
    mock_send_debug, mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_quote, mock_get_watchlist, mock_is_run_window,
):
    config = dict(BASE_CONFIG)
    config["debug_emails"] = False

    run(config=config)

    mock_send_email.assert_called_once()
    mock_send_debug.assert_not_called()


@patch("scanner.main.is_run_window", return_value=True)
@patch("scanner.main.get_watchlist", return_value=WATCHLIST)
@patch("scanner.main.get_quote", side_effect=Exception("finnhub down"))
@patch("scanner.main.get_market_trends", return_value=[])
@patch("scanner.main.build_digest", return_value="# TL;DR\nAll good.")
@patch("scanner.main.send_email")
@patch("scanner.main.send_debug_email")
def test_run_dry_run_with_errors_does_not_send_debug_email(
    mock_send_debug, mock_send_email, mock_build_digest, mock_get_trends,
    mock_get_quote, mock_get_watchlist, mock_is_run_window,
):
    config = dict(BASE_CONFIG)
    config["dry_run"] = True
    config["debug_emails"] = True

    run(config=config)

    mock_send_email.assert_not_called()
    mock_send_debug.assert_not_called()
