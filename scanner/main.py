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
