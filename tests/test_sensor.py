"""HA-side tests for PronoteLessonsTodaySensor (D-13..D-17, ENT-02, ENT-03, TIME-01)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from custom_components.ha_pronote.api import CommunicationError
from custom_components.ha_pronote.const import DOMAIN
from custom_components.ha_pronote.sensor import PronoteLessonsTodaySensor
from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers import entity_registry as er

_SENSOR_ENTITY_ID_GUESS = "sensor.jean_dupont_lessons_today"


async def test_sensor_native_value_equals_lessons_today_count(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-14 / TIME-01: native_value = len(coordinator.data.lessons_today)."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=3),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(_SENSOR_ENTITY_ID_GUESS)
    assert state is not None, list(hass.states.async_entity_ids("sensor"))
    assert state.state == "3"


async def test_sensor_unique_id_locks_d13(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-13 / ENT-02: unique_id == 'pronote_jean_dupont_lessons_today' (FROZEN v1)."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=1),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "pronote_jean_dupont_lessons_today")
    assert entity_id is not None, [
        (e.unique_id, e.entity_id) for e in registry.entities.values() if e.platform == DOMAIN
    ]


def test_sensor_class_attributes_lock_d15_d16() -> None:
    """D-15 / D-16 / ENT-03 — class-level attrs match the locked contract.

    Pure introspection, no hass fixture needed (the test is fast enough for
    the 1-second pytest timeout even though we still register the file under
    the suite — but importing the class needs no async machinery).
    """
    assert PronoteLessonsTodaySensor._attr_translation_key == "lessons_today"  # noqa: SLF001
    assert PronoteLessonsTodaySensor._attr_icon == "mdi:school"  # noqa: SLF001
    assert PronoteLessonsTodaySensor._attr_state_class == SensorStateClass.MEASUREMENT  # noqa: SLF001
    assert PronoteLessonsTodaySensor._attr_native_unit_of_measurement == "lessons"  # noqa: SLF001
    assert PronoteLessonsTodaySensor._attr_has_entity_name is True  # noqa: SLF001
    # D-14 — Phase 3 ships state-only; no class-level extra-state-attribute payload.
    assert not hasattr(PronoteLessonsTodaySensor, "_attr_extra_state_attributes")


async def test_sensor_state_class_attribute_in_state(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-16: state.attributes['state_class'] == 'measurement' (graphable in HA stats)."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=2),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(_SENSOR_ENTITY_ID_GUESS)
    assert state is not None
    assert state.attributes.get("state_class") == "measurement"
    assert state.attributes.get("unit_of_measurement") == "lessons"


async def test_sensor_no_lessons_attribute_in_state(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-14: Phase 3 sensor is state-only; no J/J+1 lesson list in attributes (Phase 4 adds TIME-02)."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=2),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(_SENSOR_ENTITY_ID_GUESS)
    assert state is not None
    assert "lessons" not in state.attributes
    assert "lessons_today" not in state.attributes
    assert "lessons_tomorrow" not in state.attributes


async def test_sensor_unavailable_when_coordinator_fails(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-15 + coordinator failure -> entity unavailable on the next refresh."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=2),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator
    with patch(
        "custom_components.ha_pronote.coordinator.fetch_all",
        side_effect=CommunicationError("network down"),
    ):
        await coordinator.async_refresh()

    state = hass.states.get(_SENSOR_ENTITY_ID_GUESS)
    assert state is not None
    assert state.state == "unavailable"
