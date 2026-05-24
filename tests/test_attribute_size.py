"""CI gate: sensor state <= 255 chars AND extra_state_attributes <= 16384 bytes.

D-17: parametrised over all 3 Phase 4 sensors against the heavy_class fixture.
Fail = CI blocks merge (ratchet: once this passes, it must always pass).
HA recorder drops attributes silently when > 16384 bytes — this test catches
that BEFORE merge, not at runtime.

MAX_STATE_ATTRS_BYTES = 16384 verified in homeassistant/components/recorder/db_schema.py
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from custom_components.ha_pronote.sensor import (
    PronoteGradesSensor,
    PronoteLessonsTodaySensor,
    PronoteNotificationsSensor,
)

# D-17 hard limits (mirror HA recorder constants)
MAX_STATE_CHARS = 255
MAX_ATTRS_BYTES = 16384  # 16 KiB exactly


@pytest.mark.parametrize(
    "sensor_cls,entity_id_fragment",
    [
        (PronoteLessonsTodaySensor, "lessons_today"),
        (PronoteGradesSensor, "notes"),
        (PronoteNotificationsSensor, "notifications"),
    ],
)
async def test_sensor_within_ha_size_limits(
    hass,
    mock_config_entry,
    mock_pronote_client,
    heavy_class_snapshot,
    sensor_cls,
    entity_id_fragment,
) -> None:
    """D-17 — state <= 255 chars AND attrs <= 16384 bytes AND not unknown/unavailable.

    No pytest.skip paths — HARD CI fail on any breach.
    heavy_class fixture: 128 lessons, 100 grades, 30 infos (D-16 generator).
    """
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=heavy_class_snapshot,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Find the matching sensor entity by entity_id fragment
    all_sensor_ids = hass.states.async_entity_ids("sensor")
    matching = [eid for eid in all_sensor_ids if entity_id_fragment in eid]
    assert len(matching) >= 1, (
        f"No sensor entity with '{entity_id_fragment}' in id. "
        f"Found: {all_sensor_ids}"
    )
    entity_state = hass.states.get(matching[0])
    assert entity_state is not None

    # Assertion 1: state is not unknown/unavailable (D-17)
    assert entity_state.state not in (None, "unknown", "unavailable"), (
        f"{sensor_cls.__name__} state is {entity_state.state!r} on heavy_class fixture. "
        f"Entity id: {matching[0]}"
    )

    # Assertion 2: state string length <= 255 chars (HA state machine limit)
    state_len = len(str(entity_state.state))
    assert state_len <= MAX_STATE_CHARS, (
        f"{sensor_cls.__name__} state len = {state_len} > {MAX_STATE_CHARS}"
    )

    # Assertion 3: attributes JSON byte size <= 16384 bytes (HA recorder limit)
    # Use default=str to handle dates/datetimes exactly as HA recorder would.
    attrs_json = json.dumps(entity_state.attributes, default=str)
    attrs_bytes = len(attrs_json.encode("utf-8"))
    assert attrs_bytes <= MAX_ATTRS_BYTES, (
        f"{sensor_cls.__name__} attrs = {attrs_bytes} bytes > {MAX_ATTRS_BYTES} bytes. "
        f"Reduce attribute payload or increase truncation limits."
    )
