"""Sensor platform — D-13, D-14, D-15, D-16, TIME-01, ENT-02.

Phase 3 ships ONE sensor (PronoteLessonsTodaySensor) — the count of today's
lessons (D-14). Phase 4 adds grades, notifications, and the J/J+1 attribute
payload on this sensor (TIME-02). Until then, the sensor is state-only:
``native_value = len(coordinator.data.lessons_today)`` — no extra
state attribute payload (D-14 — adding TIME-02 in Phase 4 is a deliberate
add, not a refactor).

unique_id (D-13, ENT-02): ``f"pronote_{child_identifier}_lessons_today"`` —
FROZEN v1, never altered by nickname (Phase 6's OPT-03 only changes display
name, never the unique_id).

translation_key (ENT-03): ``"lessons_today"`` — must match the
``entity.sensor.lessons_today.name`` key in strings.json (Plan 01).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .entity import PronoteEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import PronoteDataUpdateCoordinator
    from .data import PronoteConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PronoteConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Forward platform setup — Phase 3 ships ONE sensor; Phase 4 adds more."""
    coordinator: PronoteDataUpdateCoordinator = entry.runtime_data.coordinator
    async_add_entities([PronoteLessonsTodaySensor(coordinator, entry)])


class PronoteLessonsTodaySensor(PronoteEntity, SensorEntity):
    """TIME-01 — count of today's lessons (D-14, D-16).

    State-only in Phase 3 (no extra state attribute payload). Phase 4 adds
    the J/J+1 lesson list payload (TIME-02, TIME-03 — under HA's 16 KiB
    attribute size limit).
    """

    _attr_translation_key = "lessons_today"  # ENT-03 -> strings.json
    _attr_icon = "mdi:school"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "lessons"

    def __init__(
        self,
        coordinator: PronoteDataUpdateCoordinator,
        entry: PronoteConfigEntry,
    ) -> None:
        """Lock unique_id per D-13 — FROZEN v1, never re-derived."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"pronote_{entry.runtime_data.child_identifier}_lessons_today"

    @property
    def native_value(self) -> int:
        """D-14 / TIME-01 — count of today's lessons (Snapshot.lessons_today)."""
        return len(self.coordinator.data.lessons_today)
