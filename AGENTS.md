# AGENTS.md

## Cursor Cloud specific instructions

This repo is an automated daily stock-watchlist digest. Two parts:

- `scanner/` — Python pipeline (the core app), run as a CLI / GitHub Action
  via `python3 -m scanner.main --force`. It fetches quotes/news (Finnhub),
  the watchlist (Supabase), writes an AI digest (Ollama Cloud) and emails it
  (Gmail SMTP). A full run needs the real secrets listed in `.env.example`
  and makes live network calls, so it can't run end-to-end without them.
  Note: without an `OLLAMA_API_KEY` the digest falls back to a non-AI summary
  (`build_fallback_digest`), but Supabase/Finnhub/Gmail are still required.
- `web/` — static HTML/JS Supabase watchlist form. Serve it with any static
  server, e.g. `python3 -m http.server` from `web/`. The "Connect" screen
  needs a real Supabase URL + anon key + shared secret to load/add tickers.

### Running / testing

- Use `python3` (not `python`) and `python3 -m pytest` — the `pytest` console
  script is installed under `~/.local/bin`, which is not on `PATH`.
- Tests: `python3 -m pytest -v`. All external calls are mocked; the suite makes
  no real network calls and needs no env vars or secrets.
- There is no lint/type-check tooling configured (no ruff/flake8/black/mypy).
- Per `CLAUDE.md`, run `pytest -v` before committing changes under `scanner/`.
- CI targets Python 3.11; the VM has 3.12, which runs the suite fine.
