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
