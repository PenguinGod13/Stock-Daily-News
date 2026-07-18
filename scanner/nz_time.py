from datetime import datetime
from zoneinfo import ZoneInfo

NZ_TZ = ZoneInfo("Pacific/Auckland")


def is_run_window(now=None, target_hour=6, tolerance_minutes=30):
    if now is None:
        now = datetime.now(NZ_TZ)
    nz_now = now.astimezone(NZ_TZ)
    now_minutes = nz_now.hour * 60 + nz_now.minute
    target_minutes = target_hour * 60
    return abs(now_minutes - target_minutes) <= tolerance_minutes
