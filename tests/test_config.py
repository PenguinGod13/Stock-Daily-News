import pytest

from scanner.config import get_config, BIG_MOVE_THRESHOLD_PCT

REQUIRED_VARS = {
    "OLLAMA_API_KEY": "ollama-key",
    "FINNHUB_API_KEY": "finnhub-key",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key",
    "GMAIL_ADDRESS": "me@gmail.com",
    "GMAIL_APP_PASSWORD": "app-password",
    "RECIPIENT_EMAIL": "me@gmail.com",
}


def _set_all_required(monkeypatch):
    for key, value in REQUIRED_VARS.items():
        monkeypatch.setenv(key, value)


def test_get_config_reads_required_env_vars(monkeypatch):
    _set_all_required(monkeypatch)
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("DEBUG_EMAILS", raising=False)

    config = get_config()

    assert config["ollama_api_key"] == "ollama-key"
    assert config["finnhub_api_key"] == "finnhub-key"
    assert config["supabase_url"] == "https://example.supabase.co"
    assert config["supabase_service_key"] == "service-key"
    assert config["gmail_address"] == "me@gmail.com"
    assert config["gmail_app_password"] == "app-password"
    assert config["recipient_email"] == "me@gmail.com"
    assert config["dry_run"] is False
    assert config["debug_emails"] is True


def test_get_config_reads_dry_run_true(monkeypatch):
    _set_all_required(monkeypatch)
    monkeypatch.setenv("DRY_RUN", "true")

    config = get_config()

    assert config["dry_run"] is True


def test_get_config_missing_required_var_raises(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    with pytest.raises(KeyError):
        get_config()


def test_big_move_threshold_constant():
    assert BIG_MOVE_THRESHOLD_PCT == 3.0
