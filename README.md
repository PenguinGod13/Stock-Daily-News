# Stock Watchlist Morning Digest

Tracks a personal stock watchlist and emails a daily AI-written digest of
big moves, news, and hot sectors. See
`docs/superpowers/specs/2026-07-18-stock-digest-design.md` for the full
design.

## Setup

1. **Supabase project**
   - Create a free project at supabase.com.
   - Open the SQL Editor, replace the two `REPLACE_WITH_YOUR_SHARED_SECRET`
     placeholders in `supabase/schema.sql` with a long random string of your
     choosing, then run the file.
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
   - The repo must be public for GitHub Pages to work on a free GitHub
     plan (Settings -> General -> Danger Zone -> Change visibility).
   - In Settings -> Pages, set "Build and deployment: Source" to
     **GitHub Actions**. `.github/workflows/deploy-pages.yml` handles
     publishing `web/` on every push to `master` that touches that
     directory (or trigger it manually from the Actions tab the first
     time).
   - Open the published page, enter the Supabase URL, anon key, and the
     shared secret from step 1 to connect (or use a one-time setup link:
     `<page-url>/#url=<supabase-url>&anonKey=<anon-key>&secret=<shared-secret>`
     — note the `#`, not `?`, so the values never leave the browser — which
     saves them to that browser automatically on first visit).

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
