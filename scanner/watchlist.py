import re

import requests

# Old-style Supabase keys were JWTs (three dot-separated segments) and
# needed to be sent as both `apikey` and `Authorization: Bearer`. The
# newer sb_secret_/sb_publishable_ keys are not JWTs — sending them via
# Authorization: Bearer makes Supabase try to parse them as a JWT and
# reject the request, so that header is only added for the old format.
_JWT_PATTERN = re.compile(r"^[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]*$")


def get_watchlist(supabase_url, supabase_service_key):
    headers = {"apikey": supabase_service_key}
    if _JWT_PATTERN.match(supabase_service_key):
        headers["Authorization"] = f"Bearer {supabase_service_key}"

    resp = requests.get(
        f"{supabase_url}/rest/v1/watchlist",
        params={"select": "*"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
