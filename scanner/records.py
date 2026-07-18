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
