"""Constants for HA-Pronote."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "ha_pronote"

# Phase 2 additions (D-15, D-18) — defaults consumed by Phase 3 coordinator.
# NOT imported by api/ — fetcher.py takes today / school_tz as arguments
# (D-17, D-18) so the api/ subpackage stays free of ambient state.
DEFAULT_SCHOOL_TZ: Final = "Pacific/Noumea"
DEFAULT_LOOKBACK_DAYS: Final = 7  # J-7
DEFAULT_LOOKAHEAD_DAYS: Final = 14  # J+14

# Phase 3 additions (D-24, D-25) — HA-side runtime defaults consumed by the
# coordinator (update_interval) and __init__.py (platform forwarding).
DEFAULT_REFRESH_INTERVAL: Final = timedelta(minutes=30)  # D-24 — Phase 5 makes adaptive
PLATFORMS: Final = (Platform.SENSOR,)  # D-25 — Phase 4 adds CALENDAR
