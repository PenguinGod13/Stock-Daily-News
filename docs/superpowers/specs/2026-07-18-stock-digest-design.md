# Stock Watchlist Morning Digest — Design

## Overview

A personal tool for tracking a watchlist of stocks (watched and/or owned). Tickers
are managed through a simple web form. Every morning at 6 AM New Zealand time, an
automated job scans price data and news for each ticker plus the broader market,
uses an AI model to synthesize a digest covering big moves, trends, and hot
sectors, and emails the result via Gmail.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Web form (you)   │ ──────▶ │  Supabase (free)  │
│  GitHub Pages,     │ direct  │  Postgres table:  │
│  static HTML/JS    │  R/W    │  watchlist        │
└─────────────────┘         └─────────┬─────────┘
                                       │ read
                                       ▼
┌───────────────────────────────────────────────────┐
│  GitHub Actions (cron, runs daily)                  │
│  Python script:                                     │
│   1. Load watchlist from Supabase                    │
│   2. Fetch quotes + news per ticker (Finnhub)         │
│   3. Web search for market/sector trends (Ollama)     │
│   4. Compute % move, flag "big movers", P&L for owned │
│   5. Send everything to Ollama Cloud API → digest     │
│   6. Render HTML email, send via Gmail SMTP            │
└───────────────────────────────────────────────────┘
                                       │
                                       ▼
                              Inbox, ~6 AM NZ time
```

Five components: a static form, a Supabase database, one Python script, a GitHub
Actions cron trigger, and Gmail for sending. No always-on servers; everything
runs on free tiers.

## Components

### 1. Watchlist web form

- Static HTML/JS page hosted free on GitHub Pages.
- Talks directly to Supabase via the Supabase JS client — no custom backend needed.
- Single-user access is gated by a shared secret checked against a Supabase Row
  Level Security policy (not full multi-user auth — overkill for one person).
- Lets you add/edit/delete tickers, toggle "owned", and when owned, capture
  shares and cost basis. Optional free-text notes per ticker.

### 2. Supabase database

Table `watchlist`:

| column        | type      | notes                                  |
|---------------|-----------|-----------------------------------------|
| `id`          | uuid, PK  | auto                                     |
| `ticker`      | text      | e.g. `AAPL`, stored uppercased            |
| `owned`       | boolean   | currently held?                           |
| `shares`      | numeric, nullable | only meaningful if `owned`         |
| `cost_basis`  | numeric, nullable | average price paid per share       |
| `notes`       | text, nullable | optional free text                    |
| `created_at`  | timestamp | auto                                      |

RLS: writes require the shared secret; the scanner script reads using a
Supabase service key (stored as a GitHub Actions secret, never exposed to the
public form).

### 3. Scanner script (Python, runs inside GitHub Actions)

Flow:

1. Load watchlist rows from Supabase (service key).
2. For each ticker, call Finnhub `/quote` (current price + previous close →
   % change) and `/company-news` (recent headlines). This is the numeric/
   structured backbone — price data always comes from here, never from web
   search, since search results don't reliably yield a trustworthy % change.
3. Use Ollama Cloud's hosted web search tool to look for broader market/
   sector trends and themes — this covers the "hot sectors" angle with
   actual open-web coverage rather than being limited to Finnhub's fixed
   news database. If the web search call fails, fall back to Finnhub
   `/news?category=general` for this section instead (see "Error handling").
4. Compute `is_mover = abs(pct_change) >= 3%` (threshold is a tunable
   constant). For owned rows, compute unrealized P&L:
   `(current_price - cost_basis) * shares`.
5. Assemble a structured payload: one record per ticker (with its Finnhub
   headlines) plus the market/sector trends gathered in step 3.
6. Call the Ollama Cloud hosted API with that payload, prompting for a digest
   with four sections (see "Digest content" below).
7. If the AI call fails: retry once, then fall back to a plain rule-based
   template (raw stats + top headlines, no narrative) so an email still goes
   out.
8. Render the digest (Markdown → simple HTML) and send via Gmail SMTP (app
   password) to the recipient address.
9. Collect any errors hit during the run. If `DEBUG_EMAILS=true`, send a
   separate short "⚠️ Debug report" email summarizing them, independent of
   whether the main digest still sent (see "Error handling").

Per-ticker record shape passed to the AI step:

```
{ ticker, current_price, pct_change, is_mover, owned, shares, cost_basis,
  unrealized_pl, notes, top_headlines: [...] }
```

`notes` is your free-text field from the watchlist (e.g. "watching for
earnings") — passed through as context for the AI, not just stored inertly.

If a ticker is marked `owned` but `shares` or `cost_basis` is missing,
`unrealized_pl` is omitted for that ticker rather than erroring.

### 4. Scheduling

GitHub Actions workflow, two cron triggers to stay correct across NZ's
daylight-saving shifts without manual seasonal updates:

```yaml
on:
  schedule:
    - cron: '0 17 * * *'   # covers 6 AM NZDT (UTC+13, ~Sep–Apr)
    - cron: '0 18 * * *'   # covers 6 AM NZST (UTC+12, ~Apr–Sep)
  workflow_dispatch:        # manual "run now" trigger, for testing
```

The script checks the actual current time in `Pacific/Auckland` at the start
of each run; if it isn't approximately 6 AM NZ time right now, it exits
immediately without doing anything. Only one of the two triggers actually
sends an email on any given day, and the behavior self-corrects for daylight
saving automatically.

Runs every day (not just weekdays) by default — a weekend/holiday digest
still covers the last trading session plus any news. Can be restricted to
weekdays later if preferred.

### 5. Secrets (GitHub Actions repo secrets)

- `OLLAMA_API_KEY` (used for both the digest synthesis call and the web
  search tool call)
- `FINNHUB_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `RECIPIENT_EMAIL`

## "Big move" detection

- Threshold: `abs(daily % change) >= 3%` (tunable constant, easy to adjust
  later).
- Based on Finnhub `/quote`: current price vs. previous close.
- Owned positions additionally surface unrealized P&L based on shares and
  cost basis.

## Digest content & structure

The AI-written digest has four sections:

1. **TL;DR** — 2-3 sentences on the overall morning picture.
2. **Your movers** — owned/watched tickers that crossed the move threshold,
   with headline-derived context and P&L for owned ones.
3. **Rest of your watchlist** — one brief line per remaining ticker.
4. **Market pulse & hot sectors** — themes/sectors surfaced via web search,
   including ones outside your current watchlist.

Delivered as HTML email, subject line like `Morning Digest — Tue Jul 21`.

## Error handling

- **Per-ticker fetch failure** (bad symbol, transient API error): log, skip
  that ticker, note "couldn't fetch data for X" in the digest, continue with
  the rest.
- **Ollama Cloud call fails or times out**: retry once, then fall back to the
  plain rule-based template.
- **Ollama web search call fails**: fall back to Finnhub
  `/news?category=general` for the market/sector pulse section instead, so
  that section degrades to "less rich" rather than missing entirely.
- **Gmail send failure**: the GitHub Actions run itself fails, surfacing as a
  visible failure in the Actions tab / GitHub notifications.
- **Empty watchlist**: skip the run entirely, nothing to send.
- **Rate limits**: Finnhub free tier (60 calls/min) is far above
  personal-watchlist scale; the script adds small inter-call delays as a
  safety margin regardless.
- **Early-stage bug visibility**: while this is new and stabilizing, any
  error encountered during a run (any of the above) is collected and, if
  `DEBUG_EMAILS=true`, emailed separately as a short debug report — so
  problems surface immediately instead of sitting only in the Actions log.
  This is a toggle, meant to be turned off once things are stable, at which
  point GitHub's normal run-failure notifications are enough.

## Testing

- `DRY_RUN=true`: the composed email is printed to the workflow log instead
  of being sent — safe to iterate without spamming the inbox.
- `workflow_dispatch` manual trigger: run the full pipeline on demand from
  the GitHub Actions tab, any time, not just at the scheduled hour.
- A real end-to-end send is used once to confirm formatting/deliverability
  before relying on the daily cron.

## Known trade-offs / out of scope

- Ollama Cloud's open-source models are likely less polished at nuanced
  financial-narrative writing than frontier hosted models (GPT-4o / Claude /
  Gemini). Accepted trade-off for cost/preference reasons. The AI call is an
  isolated step, so the model or provider can be swapped later without
  touching the rest of the pipeline.
- No full user authentication on the web form — a shared-secret gate is
  sufficient for single-user use.
- No intraday/real-time alerting — this is a once-daily digest, not a live
  monitor.
- No historical backtesting or portfolio performance charting — just a daily
  snapshot plus AI narrative.

## Open questions for implementation

- Exact GitHub repo name/location (new repo vs. using this existing
  directory).
- Which specific Ollama Cloud model to use.
- Expected watchlist size (affects run time/cost, not the design itself).
