from datetime import datetime
from zoneinfo import ZoneInfo

from scanner.nz_time import is_run_window


def test_is_run_window_true_at_6am_nzdt():
    now = datetime(2026, 1, 15, 6, 5, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is True


def test_is_run_window_true_at_6am_nzst():
    now = datetime(2026, 7, 15, 6, 5, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is True


def test_is_run_window_false_at_noon():
    now = datetime(2026, 7, 15, 12, 0, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now) is False


def test_is_run_window_converts_from_utc():
    # 17:00 UTC in January = 6am NZDT (UTC+13)
    now = datetime(2026, 1, 15, 17, 0, tzinfo=ZoneInfo("UTC"))
    assert is_run_window(now) is True


def test_is_run_window_respects_tolerance_boundary():
    now = datetime(2026, 7, 15, 6, 30, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now, tolerance_minutes=30) is True
    now_outside = datetime(2026, 7, 15, 6, 31, tzinfo=ZoneInfo("Pacific/Auckland"))
    assert is_run_window(now_outside, tolerance_minutes=30) is False
