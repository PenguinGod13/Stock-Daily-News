# Stock Watchlist Morning Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated system that reads a personal stock watchlist, scans price data and news each morning, uses an AI model to synthesize a digest of big moves/trends/hot sectors, and emails it — fully on free-tier infrastructure with no always-on server.

**Architecture:** A static web form (GitHub Pages + Supabase JS client) manages the watchlist in a Supabase Postgres table. A Python scanner script — decomposed into small, independently testable modules (config, time gate, watchlist, market data, records, trends, digest, emailer, orchestration) — runs inside a GitHub Actions cron workflow, pulls price/news data from Finnhub, gathers market/sector trends via Ollama Cloud's web search tool, synthesizes the digest via Ollama Cloud chat, and sends the result over Gmail SMTP.

**Tech Stack:** Python 3.11, `requests`, `supabase-py`, `markdown`, `pytest`, GitHub Actions, Supabase (Postgres + RLS), Finnhub API, Ollama Cloud API (`/api/chat`, `/api/web_search`), Gmail SMTP, vanilla HTML/JS + Supabase JS client for the form.

## Global Constraints

- Big-move threshold: `abs(daily % change) >= 3.0` (exact value from spec, defined once as a constant).
- Target send time: 6:00 AM `Pacific/Auckland` time, every day (not just weekdays).
- GitHub Actions cron triggers: `0 17 * * *` and `0 18 * * *` (UTC), plus `workflow_dispatch` for manual runs.
- Required secrets (exact names): `OLLAMA_API_KEY`, `FINNHUB_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`.
- Env toggles: `DRY_RUN` (print instead of send, default false), `DEBUG_EMAILS` (send separate error report, default true).
- Digest has exactly four sections: TL;DR, Your movers, Rest of your watchlist, Market pulse & hot sectors.
- Supabase `watchlist` table columns: `id` (uuid PK), `ticker` (text), `owned` (boolean), `shares` (numeric, nullable), `cost_basis` (numeric, nullable), `notes` (text, nullable), `created_at` (timestamp).
- Price/% change always comes from Finnhub `/quote`, never from web search (per spec — search doesn't reliably yield trustworthy numeric data).
- Ollama Cloud REST endpoints (verified against official docs): chat at `POST https://ollama.com/api/chat` with `Authorization: Bearer $OLLAMA_API_KEY`; web search at `POST https://ollama.com/api/web_search` with the same auth header and a `query` field.
- Every task's requirements implicitly include this section.

---

## File Structure

```
scanner/
  __init__.py
  config.py       # env var loading, constants
  nz_time.py      # NZ time run-window gate
  watchlist.py    # Supabase read
  market_data.py  # Finnhub quote + company/general news
  records.py      # per-ticker record builder (mover flag, P&L)
  trends.py       # Ollama web search + Finnhub fallback
  digest.py       # Ollama chat synthesis + fallback template
  emailer.py       # markdown->html, Gmail SMTP send, debug email
  main.py         # orchestration entrypoint
tests/
  test_config.py
  test_nz_time.py
  test_watchlist.py
  test_market_data.py
  test_records.py
  test_trends.py
  test_digest.py
  test_emailer.py
  test_main.py
.github/workflows/digest.yml
supabase/schema.sql
web/index.html
web/app.js
requirements.txt
requirements-dev.txt
.env.example
README.md
CLAUDE.md
```

---

### Task 1: Project scaffolding + config module

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `scanner/__init__.py`
- Create: `scanner/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `scanner.config.get_config() -> dict` with keys `ollama_api_key`, `finnhub_api_key`, `supabase_url`, `supabase_service_key`, `gmail_address`, `gmail_app_password`, `recipient_email`, `dry_run` (bool), `debug_emails` (bool). Raises `KeyError` if a required var is missing.
- Produces: `scanner.config.BIG_MOVE_THRESHOLD_PCT` constant, value `3.0`.

- [ ] **Step 1: Create the project scaffolding files**

`requirements.txt`:
```
requests==2.32.3
supabase==2.9.1
markdown==3.7
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.3
```

`.env.example`:
```
OLLAMA_API_KEY=
FINNHUB_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
RECIPIENT_EMAIL=
DRY_RUN=false
DEBUG_EMAILS=true
```

`scanner/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.config'`

- [ ] **Step 4: Write minimal implementation**

`scanner/config.py`:
```python
import os

BIG_MOVE_THRESHOLD_PCT = 3.0


def get_config():
    return {
        "ollama_api_key": os.environ["OLLAMA_API_KEY"],
        "finnhub_api_key": os.environ["FINNHUB_API_KEY"],
        "supabase_url": os.environ["SUPABASE_URL"],
        "supabase_service_key": os.environ["SUPABASE_SERVICE_KEY"],
        "gmail_address": os.environ["GMAIL_ADDRESS"],
        "gmail_app_password": os.environ["GMAIL_APP_PASSWORD"],
        "recipient_email": os.environ["RECIPIENT_EMAIL"],
        "dry_run": os.environ.get("DRY_RUN", "false").lower() == "true",
        "debug_emails": os.environ.get("DEBUG_EMAILS", "true").lower() == "true",
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt .env.example scanner/__init__.py scanner/config.py tests/test_config.py
git commit -m "feat: add project scaffolding and config module"
```

---

### Task 2: NZ time run-window gate

**Files:**
- Create: `scanner/nz_time.py`
- Test: `tests/test_nz_time.py`

**Interfaces:**
- Consumes: none (stdlib `datetime`/`zoneinfo` only).
- Produces: `scanner.nz_time.is_run_window(now=None, target_hour=6, tolerance_minutes=30) -> bool`. When `now` is `None`, uses the current time. Accepts any timezone-aware `datetime` and converts it to `Pacific/Auckland` before comparing.

- [ ] **Step 1: Write the failing test**

`tests/test_nz_time.py`:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

from scanner.nz_time import is_run_window


def test_is_run_window_true_at_6am_nzdt():
    now = datetime(2026, 1, 15, 6, 5, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is True


def test_is_run_window_true_at_6am_nzst():
    now = datetime(2026, 7, 15, 6, 5, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is True


def test_is_run_window_false_at_noon():
    now = datetime(2026, 7, 15, 12, 0, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is False


def test_is_run_window_converts_from_utc():
    # 17:00 UTC in January = 6am NZDT (UTC+13)
    now = datetime(2026, 1, 15, 17, 0, tzinfo=ZoneInfo("UTC"))
    assert is_run_window(now) is True


def test_is_run_window_respects_tolerance_boundary():
    now = datetime(2026, 7, 15, 6, 30, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now, tolerance_minutes=30) is True
    now_outside = datetime(2026, 7, 15, 6, 31, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now_outside, tolerance_minutes=30) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_nz_time.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.nz_time'`

- [ ] **Step 3: Write minimal implementation**

`scanner/nz_time.py`:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

NZ_TZ = ZoneInfo("Pacific/Auckland")


def is_run_window(now=None, target_hour=6, tolerance_minutes=30):
    if now is None:
        now = datetime.now(NZ_TZ)
    nz_now = now.astimezone(NZ_TZ)
    now_minutes = nz_now.hour * 60 + nz_now.minute
    target_minutes = target_hour * 60
    return abs(now_minutes - target_minutes) <= tolerance_minutes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_nz_time.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/nz_time.py tests/test_nz_time.py
git commit -m "feat: add NZ time run-window gate"
```

---

### Task 3: Watchlist loading from Supabase

**Files:**
- Create: `scanner/watchlist.py`
- Test: `tests/test_watchlist.py`

**Interfaces:**
- Consumes: `supabase.create_client(url, key)` from the `supabase` package.
- Produces: `scanner.watchlist.get_watchlist(supabase_url, supabase_service_key) -> list[dict]`, where each dict has keys `ticker`, `owned`, `shares`, `cost_basis`, `notes` (matching the `watchlist` table columns).

- [ ] **Step 1: Write the failing test**

`tests/test_watchlist.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_watchlist.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.watchlist'`

- [ ] **Step 3: Write minimal implementation**

`scanner/watchlist.py`:
```python
from supabase import create_client


def get_watchlist(supabase_url, supabase_service_key):
    client = create_client(supabase_url, supabase_service_key)
    response = client.table("watchlist").select("*").execute()
    return response.data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_watchlist.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/watchlist.py tests/test_watchlist.py
git commit -m "feat: add Supabase watchlist loader"
```

---

### Task 4: Finnhub quote fetching

**Files:**
- Create: `scanner/market_data.py`
- Test: `tests/test_market_data.py`

**Interfaces:**
- Consumes: `requests.get`.
- Produces: `scanner.market_data.FINNHUB_BASE_URL` constant (`"https://finnhub.io/api/v1"`). `scanner.market_data.get_quote(ticker, api_key) -> dict` with keys `current_price`, `previous_close`, `pct_change` (float, percent, e.g. `10.0` for +10%). Raises on non-2xx via `requests`' `raise_for_status()`.

- [ ] **Step 1: Write the failing test**

`tests/test_market_data.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_data.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.market_data'`

- [ ] **Step 3: Write minimal implementation**

`scanner/market_data.py`:
```python
import requests

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_quote(ticker, api_key):
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/quote",
        params={"symbol": ticker, "token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    current_price = data["c"]
    previous_close = data["pc"]
    pct_change = (
        ((current_price - previous_close) / previous_close) * 100
        if previous_close
        else 0.0
    )
    return {
        "current_price": current_price,
        "previous_close": previous_close,
        "pct_change": pct_change,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_data.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/market_data.py tests/test_market_data.py
git commit -m "feat: add Finnhub quote fetching"
```

---

### Task 5: Finnhub company and general news fetching

**Files:**
- Modify: `scanner/market_data.py`
- Modify: `tests/test_market_data.py`

**Interfaces:**
- Consumes: `scanner.market_data.FINNHUB_BASE_URL` (from Task 4).
- Produces: `scanner.market_data.get_company_news(ticker, api_key, days=2, limit=3) -> list[dict]` with keys `headline`, `url`. `scanner.market_data.get_general_news(api_key, limit=8) -> list[dict]` with keys `headline`, `url`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_market_data.py`:
```python
from datetime import date, timedelta


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
```

Update the import line at the top of `tests/test_market_data.py`:
```python
from scanner.market_data import get_quote, get_company_news, get_general_news
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_data.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_company_news'`

- [ ] **Step 3: Write minimal implementation**

Append to `scanner/market_data.py`:
```python
from datetime import date, timedelta


def get_company_news(ticker, api_key, days=2, limit=3):
    to_date = date.today()
    from_date = to_date - timedelta(days=days)
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/company-news",
        params={
            "symbol": ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": api_key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json()
    return [{"headline": a["headline"], "url": a["url"]} for a in articles[:limit]]


def get_general_news(api_key, limit=8):
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/news",
        params={"category": "general", "token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    articles = resp.json()
    return [{"headline": a["headline"], "url": a["url"]} for a in articles[:limit]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_market_data.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/market_data.py tests/test_market_data.py
git commit -m "feat: add Finnhub company and general news fetching"
```

---

### Task 6: Per-ticker record builder (mover flag + P&L)

**Files:**
- Create: `scanner/records.py`
- Test: `tests/test_records.py`

**Interfaces:**
- Consumes: `scanner.config.BIG_MOVE_THRESHOLD_PCT` (Task 1); a watchlist row dict (Task 3 shape: `ticker`, `owned`, `shares`, `cost_basis`, `notes`); a quote dict (Task 4 shape: `current_price`, `previous_close`, `pct_change`); a headlines list (Task 5 shape: list of `{headline, url}`).
- Produces: `scanner.records.build_ticker_record(watchlist_row, quote, headlines) -> dict` with keys `ticker`, `current_price`, `pct_change`, `is_mover`, `owned`, `shares`, `cost_basis`, `unrealized_pl`, `notes`, `top_headlines`. `unrealized_pl` is `None` unless `owned` is true and both `shares` and `cost_basis` are present.

- [ ] **Step 1: Write the failing test**

`tests/test_records.py`:
```python
from scanner.records import build_ticker_record


def _quote(current_price, pct_change):
    return {"current_price": current_price, "previous_close": None, "pct_change": pct_change}


def test_build_ticker_record_flags_big_mover():
    row = {"ticker": "AAPL", "owned": False, "shares": None, "cost_basis": None, "notes": None}
    quote = _quote(110.0, 5.0)
    headlines = [{"headline": "AAPL surges", "url": "https://example.com/1"}]

    record = build_ticker_record(row, quote, headlines)

    assert record["ticker"] == "AAPL"
    assert record["current_price"] == 110.0
    assert record["pct_change"] == 5.0
    assert record["is_mover"] is True
    assert record["owned"] is False
    assert record["unrealized_pl"] is None
    assert record["top_headlines"] == headlines


def test_build_ticker_record_not_mover_below_threshold():
    row = {"ticker": "MSFT", "owned": False, "shares": None, "cost_basis": None, "notes": None}
    quote = _quote(101.0, 1.0)

    record = build_ticker_record(row, quote, [])

    assert record["is_mover"] is False


def test_build_ticker_record_negative_move_counts_as_mover():
    row = {"ticker": "TSLA", "owned": False, "shares": None, "cost_basis": None, "notes": None}
    quote = _quote(90.0, -4.0)

    record = build_ticker_record(row, quote, [])

    assert record["is_mover"] is True


def test_build_ticker_record_computes_unrealized_pl_when_owned():
    row = {"ticker": "AAPL", "owned": True, "shares": 10, "cost_basis": 100.0, "notes": "long term hold"}
    quote = _quote(110.0, 10.0)

    record = build_ticker_record(row, quote, [])

    assert record["unrealized_pl"] == 100.0
    assert record["notes"] == "long term hold"


def test_build_ticker_record_omits_pl_when_owned_but_missing_shares():
    row = {"ticker": "AAPL", "owned": True, "shares": None, "cost_basis": 100.0, "notes": None}
    quote = _quote(110.0, 10.0)

    record = build_ticker_record(row, quote, [])

    assert record["unrealized_pl"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_records.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.records'`

- [ ] **Step 3: Write minimal implementation**

`scanner/records.py`:
```python
from scanner.config import BIG_MOVE_THRESHOLD_PCT


def build_ticker_record(watchlist_row, quote, headlines):
    owned = watchlist_row.get("owned", False)
    shares = watchlist_row.get("shares")
    cost_basis = watchlist_row.get("cost_basis")
    pct_change = quote["pct_change"]
    is_mover = abs(pct_change) >= BIG_MOVE_THRESHOLD_PCT

    unrealized_pl = None
    if owned and shares is not None and cost_basis is not None:
        unrealized_pl = (quote["current_price"] - cost_basis) * shares

    return {
        "ticker": watchlist_row["ticker"],
        "current_price": quote["current_price"],
        "pct_change": pct_change,
        "is_mover": is_mover,
        "owned": owned,
        "shares": shares,
        "cost_basis": cost_basis,
        "unrealized_pl": unrealized_pl,
        "notes": watchlist_row.get("notes"),
        "top_headlines": headlines,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_records.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/records.py tests/test_records.py
git commit -m "feat: add per-ticker record builder with mover flag and P&L"
```

---

### Task 7: Market trends via Ollama web search, with Finnhub fallback

**Files:**
- Create: `scanner/trends.py`
- Test: `tests/test_trends.py`

**Interfaces:**
- Consumes: `requests.post`; `scanner.market_data.get_general_news(api_key, limit=8)` (Task 5).
- Produces: `scanner.trends.get_market_trends(ollama_api_key, finnhub_api_key) -> list[dict]`, each item `{"title": str, "url": str, "content": str}`. On web-search failure, falls back to Finnhub general news mapped into the same shape (`content` is `""`).

- [ ] **Step 1: Write the failing test**

`tests/test_trends.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trends.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.trends'`

- [ ] **Step 3: Write minimal implementation**

`scanner/trends.py`:
```python
import requests

from scanner.market_data import get_general_news

OLLAMA_WEB_SEARCH_URL = "https://ollama.com/api/web_search"


def get_market_trends(ollama_api_key, finnhub_api_key):
    try:
        resp = requests.post(
            OLLAMA_WEB_SEARCH_URL,
            headers={"Authorization": f"Bearer {ollama_api_key}"},
            json={"query": "stock market trends and hot sectors today", "max_results": 8},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
            for r in data.get("results", [])
        ]
    except Exception:
        articles = get_general_news(finnhub_api_key)
        return [{"title": a["headline"], "url": a["url"], "content": ""} for a in articles]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trends.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/trends.py tests/test_trends.py
git commit -m "feat: add market trends via Ollama web search with Finnhub fallback"
```

---

### Task 8: Digest synthesis via Ollama chat, with fallback template

**Files:**
- Create: `scanner/digest.py`
- Test: `tests/test_digest.py`

**Interfaces:**
- Consumes: `requests.post`; ticker records list (Task 6 shape); market trends list (Task 7 shape).
- Produces: `scanner.digest.build_digest(ollama_api_key, ticker_records, market_trends, model="gpt-oss:120b") -> str` (Markdown text). Retries the Ollama call once on failure, then falls back to `build_fallback_digest(ticker_records, market_trends)`.
- Produces: `scanner.digest.build_fallback_digest(ticker_records, market_trends) -> str` (Markdown text, rule-based, no AI).

- [ ] **Step 1: Write the failing test**

`tests/test_digest.py`:
```python
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
    result = build_fallback_digest(TICKER_RECORDS, MARKET_TRENDS)

    assert "AAPL" in result
    assert "10.00%" in result
    assert "100.00" in result
    assert "MSFT" in result
    assert "AI chip demand surges" in result


def test_build_fallback_digest_handles_no_movers():
    no_movers = [dict(r, is_mover=False) for r in TICKER_RECORDS]

    result = build_fallback_digest(no_movers, MARKET_TRENDS)

    assert "No tickers moved beyond the threshold" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.digest'`

- [ ] **Step 3: Write minimal implementation**

`scanner/digest.py`:
```python
import json

import requests

OLLAMA_CHAT_URL = "https://ollama.com/api/chat"

DIGEST_SYSTEM_PROMPT = """You are a financial digest writer. You will receive JSON \
describing a user's stock watchlist (with price moves, ownership, and recent \
headlines) and broader market/sector trends. Write a concise morning digest in \
Markdown with exactly these four sections, in this order:

1. TL;DR - 2-3 sentences on the overall morning picture.
2. Your movers - watchlist tickers where is_mover is true, with brief context \
from their headlines, and unrealized P&L for owned tickers where available.
3. Rest of your watchlist - one short line per remaining ticker.
4. Market pulse & hot sectors - themes/sectors from the market trends data, \
including ones outside the user's watchlist.

Be factual and concise. Do not invent price data or headlines not present in \
the input."""


def build_prompt(ticker_records, market_trends):
    return json.dumps({"tickers": ticker_records, "market_trends": market_trends})


def call_ollama_chat(ollama_api_key, prompt, model="gpt-oss:120b"):
    resp = requests.post(
        OLLAMA_CHAT_URL,
        headers={"Authorization": f"Bearer {ollama_api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def build_fallback_digest(ticker_records, market_trends):
    lines = ["# Morning Digest (fallback — AI summary unavailable)", ""]

    movers = [r for r in ticker_records if r["is_mover"]]
    lines.append("## Your movers")
    if movers:
        for r in movers:
            pl_str = (
                f", P&L: ${r['unrealized_pl']:.2f}"
                if r.get("unrealized_pl") is not None
                else ""
            )
            lines.append(f"- {r['ticker']}: {r['pct_change']:.2f}%{pl_str}")
    else:
        lines.append("- No tickers moved beyond the threshold today.")
    lines.append("")

    lines.append("## Rest of your watchlist")
    rest = [r for r in ticker_records if not r["is_mover"]]
    if rest:
        for r in rest:
            lines.append(f"- {r['ticker']}: {r['pct_change']:.2f}%")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Market pulse & hot sectors")
    if market_trends:
        for t in market_trends[:5]:
            lines.append(f"- {t['title']}")
    else:
        lines.append("- No market trend data available.")

    return "\n".join(lines)


def build_digest(ollama_api_key, ticker_records, market_trends, model="gpt-oss:120b"):
    prompt = build_prompt(ticker_records, market_trends)
    last_error = None
    for _ in range(2):
        try:
            return call_ollama_chat(ollama_api_key, prompt, model=model)
        except Exception as e:
            last_error = e
    return build_fallback_digest(ticker_records, market_trends)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/digest.py tests/test_digest.py
git commit -m "feat: add Ollama chat digest synthesis with fallback template"
```

---

### Task 9: Email rendering and sending (Gmail SMTP)

**Files:**
- Create: `scanner/emailer.py`
- Test: `tests/test_emailer.py`

**Interfaces:**
- Consumes: `markdown.markdown`; `smtplib.SMTP_SSL`.
- Produces: `scanner.emailer.markdown_to_html(md_text) -> str`. `scanner.emailer.send_email(gmail_address, gmail_app_password, recipient_email, subject, html_body) -> None`. `scanner.emailer.send_debug_email(gmail_address, gmail_app_password, recipient_email, errors: list[str]) -> None`.

- [ ] **Step 1: Write the failing test**

`tests/test_emailer.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_emailer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.emailer'`

- [ ] **Step 3: Write minimal implementation**

`scanner/emailer.py`:
```python
import smtplib
from email.mime.text import MIMEText

import markdown


def markdown_to_html(md_text):
    return markdown.markdown(md_text)


def send_email(gmail_address, gmail_app_password, recipient_email, subject, html_body):
    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = recipient_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [recipient_email], msg.as_string())


def send_debug_email(gmail_address, gmail_app_password, recipient_email, errors):
    body = "<h2>Debug report</h2><ul>" + "".join(f"<li>{e}</li>" for e in errors) + "</ul>"
    send_email(gmail_address, gmail_app_password, recipient_email, "⚠️ Debug report", body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_emailer.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scanner/emailer.py tests/test_emailer.py
git commit -m "feat: add markdown rendering and Gmail SMTP sending"
```

---

### Task 10: Main orchestration script

**Files:**
- Create: `scanner/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `scanner.config.get_config` (Task 1); `scanner.nz_time.is_run_window` (Task 2); `scanner.watchlist.get_watchlist` (Task 3); `scanner.market_data.get_quote`, `scanner.market_data.get_company_news` (Tasks 4-5); `scanner.records.build_ticker_record` (Task 6); `scanner.trends.get_market_trends` (Task 7); `scanner.digest.build_digest` (Task 8); `scanner.emailer.markdown_to_html`, `scanner.emailer.send_email`, `scanner.emailer.send_debug_email` (Task 9).
- Produces: `scanner.main.run(config=None, force=False) -> None`. `force=True` bypasses the NZ time-window gate (used by manual `workflow_dispatch` runs). Skips sending if the time gate fails (and not forced) or the watchlist is empty. Per-ticker fetch failures are caught, logged into an `errors` list, and skipped rather than aborting the run. If `DRY_RUN` is true, prints the email instead of sending. If there were errors and `DEBUG_EMAILS` is true and not a dry run, sends a separate debug email.

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scanner.main'`

- [ ] **Step 3: Write minimal implementation**

`scanner/main.py`:
```python
import sys
from datetime import date

from scanner.config import get_config
from scanner.nz_time import is_run_window
from scanner.watchlist import get_watchlist
from scanner.market_data import get_quote, get_company_news
from scanner.records import build_ticker_record
from scanner.trends import get_market_trends
from scanner.digest import build_digest
from scanner.emailer import markdown_to_html, send_email, send_debug_email


def run(config=None, force=False):
    config = config or get_config()
    errors = []

    if not force and not is_run_window():
        print("Outside NZ run window, exiting.")
        return

    watchlist = get_watchlist(config["supabase_url"], config["supabase_service_key"])
    if not watchlist:
        print("Empty watchlist, skipping.")
        return

    ticker_records = []
    for row in watchlist:
        ticker = row["ticker"]
        try:
            quote = get_quote(ticker, config["finnhub_api_key"])
            headlines = get_company_news(ticker, config["finnhub_api_key"])
            ticker_records.append(build_ticker_record(row, quote, headlines))
        except Exception as e:
            errors.append(f"Failed to fetch data for {ticker}: {e}")

    market_trends = get_market_trends(config["ollama_api_key"], config["finnhub_api_key"])

    digest_md = build_digest(config["ollama_api_key"], ticker_records, market_trends)
    html = markdown_to_html(digest_md)
    subject = f"Morning Digest — {date.today().strftime('%a %b %d')}"

    if config["dry_run"]:
        print(subject)
        print(html)
    else:
        send_email(
            config["gmail_address"],
            config["gmail_app_password"],
            config["recipient_email"],
            subject,
            html,
        )

    if errors and config["debug_emails"] and not config["dry_run"]:
        send_debug_email(
            config["gmail_address"],
            config["gmail_app_password"],
            config["recipient_email"],
            errors,
        )


if __name__ == "__main__":
    run(force="--force" in sys.argv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS (all tests across all modules, ~28 tests)

- [ ] **Step 6: Commit**

```bash
git add scanner/main.py tests/test_main.py
git commit -m "feat: add main orchestration script"
```

---

### Task 11: GitHub Actions cron workflow

**Files:**
- Create: `.github/workflows/digest.yml`

**Interfaces:**
- Consumes: `scanner/main.py` (Task 10) as `python -m scanner.main`, requiring env vars matching the Global Constraints secrets list.
- Produces: a GitHub Actions workflow triggered on the two cron schedules and `workflow_dispatch`.

- [ ] **Step 1: Create the workflow file**

`.github/workflows/digest.yml`:
```yaml
name: Morning Digest

on:
  schedule:
    - cron: '0 17 * * *'
    - cron: '0 18 * * *'
  workflow_dispatch:
    inputs:
      force:
        description: 'Bypass the NZ time-window gate'
        type: boolean
        default: true

jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run digest
        env:
          OLLAMA_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
          FINNHUB_API_KEY: ${{ secrets.FINNHUB_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
          DRY_RUN: ${{ vars.DRY_RUN || 'false' }}
          DEBUG_EMAILS: ${{ vars.DEBUG_EMAILS || 'true' }}
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ] && [ "${{ inputs.force }}" = "true" ]; then
            python -m scanner.main --force
          else
            python -m scanner.main
          fi
```

- [ ] **Step 2: Verify the YAML is well-formed**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/digest.yml'))"`
Expected: no output, exit code 0 (this requires `pyyaml`; if not installed, run `pip install pyyaml` first — it's only needed for this one-off check, not added to requirements.txt)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/digest.yml
git commit -m "feat: add GitHub Actions cron workflow for daily digest"
```

---

### Task 12: Supabase schema and RLS policy

**Files:**
- Create: `supabase/schema.sql`

**Interfaces:**
- Produces: SQL that creates the `watchlist` table (columns per Global Constraints) and two RLS policies: public read/write gated by a shared secret header, service-role full access for the scanner script.

- [ ] **Step 1: Write the schema file**

`supabase/schema.sql`:
```sql
create table if not exists watchlist (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  owned boolean not null default false,
  shares numeric,
  cost_basis numeric,
  notes text,
  created_at timestamptz not null default now()
);

alter table watchlist enable row level security;

-- The scanner script reads using the Supabase service role key, which
-- bypasses RLS entirely, so no explicit service-role policy is required.

-- The public web form uses the anon key. Access is gated by a shared
-- secret passed as a custom request header, checked here via a Postgres
-- setting configured per-request through PostgREST's `request.headers`.
create policy "shared secret full access"
  on watchlist
  for all
  using (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = current_setting('app.watchlist_shared_secret', true)
  )
  with check (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = current_setting('app.watchlist_shared_secret', true)
  );
```

- [ ] **Step 2: Document the manual application steps**

These steps cannot be automated from this repo — Supabase project creation and SQL execution happen in the Supabase dashboard. Record them in `README.md` (Task 14) rather than as a plan step here. For now, note in a comment at the top of `supabase/schema.sql`:

```sql
-- Apply this file via the Supabase dashboard SQL editor (Project ->
-- SQL Editor -> New query -> paste -> Run), on a fresh Supabase project.
-- After applying, set the shared secret used by the RLS policy above:
--   alter database postgres set app.watchlist_shared_secret = '<your-secret>';
-- Then reload the config: select pg_reload_conf();
```

Prepend that comment block to `supabase/schema.sql` above the `create table` line.

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat: add Supabase watchlist schema and RLS policy"
```

---

### Task 13: Watchlist web form (static HTML/JS)

**Files:**
- Create: `web/index.html`
- Create: `web/app.js`

**Interfaces:**
- Consumes: Supabase JS client (via CDN `<script>` tag, no build step); the `watchlist` table and RLS policy from Task 12 (expects an `x-watchlist-secret` header on every request).
- Produces: a static page that lists, adds, edits, and deletes watchlist rows.

- [ ] **Step 1: Create the HTML page**

`web/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Stock Watchlist</title>
  <script
    src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.110.7/dist/umd/supabase.min.js"
    integrity="sha384-BmlQlKlDvXvKoxkn5OQuUo/aJQCTXeB+Kls6EccBmG4Kf8AXvp89RtO9MtPxP/r5"
    crossorigin="anonymous"></script>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.4rem; border-bottom: 1px solid #ddd; }
    input[type="text"], input[type="number"] { width: 100%; box-sizing: border-box; }
    #setup, #app { display: none; }
    #setup.visible, #app.visible { display: block; }
    .error { color: #b00020; }
  </style>
</head>
<body>
  <div id="setup" class="visible">
    <h1>Connect</h1>
    <label>Supabase URL <input type="text" id="supabase-url" /></label><br />
    <label>Supabase anon key <input type="text" id="supabase-anon-key" /></label><br />
    <label>Shared secret <input type="text" id="shared-secret" /></label><br />
    <button id="connect-btn">Connect</button>
    <p class="error" id="setup-error"></p>
  </div>

  <div id="app">
    <h1>Stock Watchlist</h1>
    <table>
      <thead>
        <tr><th>Ticker</th><th>Owned</th><th>Shares</th><th>Cost basis</th><th>Notes</th><th></th></tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
    <h2>Add ticker</h2>
    <label>Ticker <input type="text" id="new-ticker" /></label><br />
    <label>Owned <input type="checkbox" id="new-owned" /></label><br />
    <label>Shares <input type="number" id="new-shares" /></label><br />
    <label>Cost basis <input type="number" id="new-cost-basis" /></label><br />
    <label>Notes <input type="text" id="new-notes" /></label><br />
    <button id="add-btn">Add</button>
    <p class="error" id="app-error"></p>
  </div>

  <script src="app.js"></script>
</body>
</html>
```

The script tag is pinned to `@supabase/supabase-js@2.110.7` with a verified
SHA-384 Subresource Integrity hash so the page fails closed (refuses to
execute) rather than silently running altered code if the CDN is ever
compromised. If this version is bumped later, regenerate the hash with:
`curl -s <new-cdn-url> | openssl dgst -sha384 -binary | openssl base64 -A`.

- [ ] **Step 2: Create the app logic**

`web/app.js`:
```javascript
let supabaseClient = null;
let sharedSecret = null;

function headers() {
  return { "x-watchlist-secret": sharedSecret };
}

function showApp() {
  document.getElementById("setup").classList.remove("visible");
  document.getElementById("app").classList.add("visible");
}

async function loadRows() {
  const { data, error } = await supabaseClient
    .from("watchlist")
    .select("*")
    .order("ticker");

  const errorEl = document.getElementById("app-error");
  if (error) {
    errorEl.textContent = error.message;
    return;
  }
  errorEl.textContent = "";

  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";
  for (const row of data) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.ticker}</td>
      <td>${row.owned ? "yes" : "no"}</td>
      <td>${row.shares ?? ""}</td>
      <td>${row.cost_basis ?? ""}</td>
      <td>${row.notes ?? ""}</td>
      <td><button data-id="${row.id}" class="delete-btn">Delete</button></td>
    `;
    tbody.appendChild(tr);
  }

  for (const btn of document.querySelectorAll(".delete-btn")) {
    btn.addEventListener("click", () => deleteRow(btn.dataset.id));
  }
}

async function addRow() {
  const ticker = document.getElementById("new-ticker").value.trim().toUpperCase();
  const owned = document.getElementById("new-owned").checked;
  const sharesRaw = document.getElementById("new-shares").value;
  const costBasisRaw = document.getElementById("new-cost-basis").value;
  const notes = document.getElementById("new-notes").value.trim() || null;

  if (!ticker) {
    document.getElementById("app-error").textContent = "Ticker is required.";
    return;
  }

  const { error } = await supabaseClient.from("watchlist").insert({
    ticker,
    owned,
    shares: sharesRaw ? Number(sharesRaw) : null,
    cost_basis: costBasisRaw ? Number(costBasisRaw) : null,
    notes,
  });

  const errorEl = document.getElementById("app-error");
  if (error) {
    errorEl.textContent = error.message;
    return;
  }
  errorEl.textContent = "";
  document.getElementById("new-ticker").value = "";
  document.getElementById("new-owned").checked = false;
  document.getElementById("new-shares").value = "";
  document.getElementById("new-cost-basis").value = "";
  document.getElementById("new-notes").value = "";
  await loadRows();
}

async function deleteRow(id) {
  const { error } = await supabaseClient.from("watchlist").delete().eq("id", id);
  if (error) {
    document.getElementById("app-error").textContent = error.message;
    return;
  }
  await loadRows();
}

document.getElementById("connect-btn").addEventListener("click", async () => {
  const url = document.getElementById("supabase-url").value.trim();
  const anonKey = document.getElementById("supabase-anon-key").value.trim();
  const secret = document.getElementById("shared-secret").value.trim();

  if (!url || !anonKey || !secret) {
    document.getElementById("setup-error").textContent = "All fields are required.";
    return;
  }

  sharedSecret = secret;
  supabaseClient = supabase.createClient(url, anonKey, {
    global: { headers: headers() },
  });

  showApp();
  await loadRows();
});

document.getElementById("add-btn").addEventListener("click", addRow);
```

- [ ] **Step 3: Manually verify in a browser**

Open `web/index.html` directly in a browser (`file://` URL works for this static page), enter a Supabase project URL, anon key, and the shared secret configured in Task 12, click Connect, and confirm the table loads, a new row can be added, and a row can be deleted. This step has no automated test — record the outcome in the task's commit message or PR description.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: add static watchlist web form"
```

---

### Task 14: Documentation (README + CLAUDE.md)

**Files:**
- Create: `README.md`
- Create: `CLAUDE.md`

**Interfaces:**
- Produces: setup documentation covering Supabase project creation, secret configuration, GitHub Pages deployment, and how to run tests/dry-run locally.

- [ ] **Step 1: Write the README**

`README.md`:
```markdown
# Stock Watchlist Morning Digest

Tracks a personal stock watchlist and emails a daily AI-written digest of
big moves, news, and hot sectors. See
`docs/superpowers/specs/2026-07-18-stock-digest-design.md` for the full
design.

## Setup

1. **Supabase project**
   - Create a free project at supabase.com.
   - Open the SQL Editor and run `supabase/schema.sql`.
   - Set the RLS shared secret as described in the comment at the top of
     that file.
   - Copy the project URL, anon key, and service role key.

2. **Finnhub**
   - Create a free account at finnhub.io and copy the API key.

3. **Ollama Cloud**
   - Create an account at ollama.com, generate an API key under
     Settings -> API Keys.

4. **Gmail app password**
   - Enable 2FA on the sending Gmail account, then generate an app
     password under Google Account -> Security -> App passwords.

5. **GitHub repo secrets**
   - In the repo's Settings -> Secrets and variables -> Actions, add:
     `OLLAMA_API_KEY`, `FINNHUB_API_KEY`, `SUPABASE_URL`,
     `SUPABASE_SERVICE_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`,
     `RECIPIENT_EMAIL`.
   - Optionally set repo variables `DRY_RUN` / `DEBUG_EMAILS` to override
     the workflow defaults.

6. **Web form**
   - Enable GitHub Pages for the repo, serving from the `web/` directory
     (or copy `web/index.html` and `web/app.js` to any static host).
   - Open the page, enter the Supabase URL, anon key, and the shared
     secret from step 1 to connect.

## Local development

```bash
pip install -r requirements-dev.txt
pytest -v
```

To dry-run the full pipeline locally without sending an email:

```bash
export OLLAMA_API_KEY=...
export FINNHUB_API_KEY=...
export SUPABASE_URL=...
export SUPABASE_SERVICE_KEY=...
export GMAIL_ADDRESS=...
export GMAIL_APP_PASSWORD=...
export RECIPIENT_EMAIL=...
export DRY_RUN=true
python -m scanner.main --force
```

## Schedule

Runs daily at 6:00 AM `Pacific/Auckland` time via GitHub Actions
(`.github/workflows/digest.yml`), which self-adjusts for daylight saving.
Trigger a manual run anytime from the Actions tab (`workflow_dispatch`).
```

- [ ] **Step 2: Write CLAUDE.md**

`CLAUDE.md`:
```markdown
# CLAUDE.md

## Project

Automated daily stock watchlist digest. See `README.md` for setup and
`docs/superpowers/specs/2026-07-18-stock-digest-design.md` for the design.

## Conventions

- Python modules under `scanner/` are small and single-purpose; each has a
  matching `tests/test_<module>.py`.
- External calls (Finnhub, Supabase, Ollama Cloud, Gmail SMTP) are always
  mocked in tests — no real network calls in the test suite.
- Run `pytest -v` before committing any change under `scanner/`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add README and CLAUDE.md"
```

---

## Self-Review Notes

- **Spec coverage:** web form (Task 13) + Supabase schema (Task 12) cover watchlist management; scanner modules (Tasks 3-9) cover price/news/trend gathering, mover detection, P&L, AI digest with fallback; main.py (Task 10) covers orchestration, dry-run, empty-watchlist skip, and debug-email error reporting; the GitHub Actions workflow (Task 11) covers the DST-safe dual-cron schedule and manual trigger; README (Task 14) covers secrets setup and deployment. All spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO markers; every code step has complete, runnable code.
- **Type consistency:** the ticker record shape (`ticker`, `current_price`, `pct_change`, `is_mover`, `owned`, `shares`, `cost_basis`, `unrealized_pl`, `notes`, `top_headlines`) is identical across Task 6 (producer), Task 8 (consumer in `build_digest`/`build_fallback_digest`), and Task 10 (orchestration). The market trends shape (`title`, `url`, `content`) is identical across Task 7 (producer) and Task 8 (consumer).
