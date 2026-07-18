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
