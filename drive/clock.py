"""Grimsby's own world time. One day in his world lasts about three real hours.

Day 1 starts at his hatching (first run of the old brain), at 08:00 world time.
"""

from __future__ import annotations

from datetime import datetime, timedelta

BIRTH = datetime.fromisoformat("2026-11-14T19:36:32+01:00")
REAL_SECONDS_PER_WORLD_DAY = 3 * 3600
START_MINUTE = 8 * 60                     # he hatched in the morning
TICK_SECONDS = 90                         # one tick every 90 real seconds = 12 world minutes
NIGHT_FROM, NIGHT_UNTIL = 22, 6           # world hours


def world_minutes(real: datetime) -> float:
    elapsed = (real - BIRTH).total_seconds()
    return START_MINUTE + elapsed / REAL_SECONDS_PER_WORLD_DAY * 1440


def world(real: datetime) -> dict:
    m = world_minutes(real)
    day = int(m // 1440) + 1
    mod = int(m % 1440)
    return {"day": day, "time": f"{mod // 60:02d}:{mod % 60:02d}", "hour": mod / 60}


def is_night(real: datetime) -> bool:
    h = world(real)["hour"]
    return h >= NIGHT_FROM or h < NIGHT_UNTIL


def next_tick(real: datetime) -> datetime:
    return real + timedelta(seconds=TICK_SECONDS)
