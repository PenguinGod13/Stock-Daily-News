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
