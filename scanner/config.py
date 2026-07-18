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
