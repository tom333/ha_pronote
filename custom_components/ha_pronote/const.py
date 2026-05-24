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
# D-10 — Phase 4 extends to include CALENDAR.
# __init__.py:async_forward_entry_setups(entry, PLATFORMS) already iterates this const.
PLATFORMS: Final = (Platform.SENSOR, Platform.CALENDAR)

# Phase 4 additions — event-type constants (D-13, EVENT-01..03),
# class level attribute (D-19, ENT-01), attribute caps (D-05, D-04),
# platform extension (D-10).

EVENT_SCHEDULE_CHANGED: Final = "pronote_schedule_changed"   # D-13, EVENT-01
EVENT_NEW_GRADE: Final = "pronote_new_grade"                 # D-13, EVENT-02
EVENT_NEW_INFORMATION: Final = "pronote_new_information"     # D-13, EVENT-03

# Probe-locked class level attribute on pronotepy.ClientInfo (D-19, ENT-01).
# PHASE-4-PROBE-NOTES.md STEP 11 confirms: ClientInfo.class_name returns
#   raw_resource.get("classeDEleve", {}).get("L", "") — returns "" not None when absent.
# For ParentClient, client.info.class_name is "" (parent has no class);
# the child's class lives in client.children[child_index].class_name.
CLASS_LEVEL_ATTR: Final = "class_name"

NOTIFICATIONS_WINDOW: Final = 20    # D-05 — cap on informations list in sensor attrs
GRADE_COMMENT_MAX_LEN: Final = 200  # D-04 — comment truncation length at sensor render
# D-04 (revised post-UAT): CONTEXT.md called for "all current-period grades",
# but the heavy-class CI gate (D-17 + 100 grades fixture) measured the JSON
# payload at 18 365 bytes — exceeds the 16 384-byte recorder cap. Cap the
# attribute at the 50 most recent (sorted by date desc) so the 9-field
# ApexCharts schema fits comfortably. Realistic trimester counts (~30–60)
# remain fully covered; only the synthetic 100-grade stress case is trimmed.
GRADES_WINDOW: Final = 50
