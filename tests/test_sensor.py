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
    # Phase 4 adds TIME-02 extra_state_attributes (lessons_today + lessons_tomorrow).
    # The Phase 3 assertion "no _attr_extra_state_attributes" is now REMOVED.
    # The property is defined on the instance (not as a class-level _attr), so
    # hasattr check is no longer meaningful here.


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


async def test_device_info_model_set_from_class_name(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """ENT-01 / D-19: DeviceInfo.model = ClientInfo.class_name when non-empty (eleve path)."""
    from homeassistant.helpers import device_registry as dr

    today = date(2026, 5, 7)
    mock_pronote_client.info.class_name = "3ème A"
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

    device_registry = dr.async_get(hass)
    devices = list(device_registry.devices.values())
    assert len(devices) == 1
    device = devices[0]
    assert device.manufacturer == "Pronote"
    assert device.model == "3ème A"


async def test_device_info_model_none_when_class_name_empty(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """ENT-01 / D-19: DeviceInfo.model is None when class_name == '' (HA hides the row)."""
    from homeassistant.helpers import device_registry as dr

    today = date(2026, 5, 7)
    mock_pronote_client.info.class_name = ""  # empty string -> or None
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

    device_registry = dr.async_get(hass)
    devices = list(device_registry.devices.values())
    assert len(devices) == 1
    assert devices[0].model is None


async def test_device_info_model_for_parent_client(
    hass,
    mock_config_entry,
    snapshot_with_n_lessons_today,
) -> None:
    """ENT-01 / D-19 (ParentClient path): DeviceInfo.model sources from children[child_index].

    PHASE-4-PROBE-NOTES.md STEP 11: client.info.class_name == "" for parent;
    child's class lives in client.children[child_index].class_name.
    """
    import pronotepy
    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.ha_pronote.const import DOMAIN

    from unittest.mock import MagicMock

    today = date(2026, 5, 7)

    # Simulate a ParentClient mock
    parent_client = MagicMock(spec=pronotepy.ParentClient)
    parent_client.info.name = "M. GUYADER Thomas"
    parent_client.info.class_name = ""  # parent has no class (probe-confirmed)
    child_mock = MagicMock()
    child_mock.class_name = "504"
    parent_client.children = [child_mock]
    parent_client.current_period = MagicMock()
    parent_client.current_period.grades = []
    parent_client.lessons = MagicMock(return_value=[])
    parent_client.information_and_surveys = MagicMock(return_value=[])
    parent_client.export_credentials = MagicMock(return_value={"token": "parent_tok"})
    parent_client.set_child = MagicMock()

    parent_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:parent:guyader_sacha",
        data={
            "url": "https://example.com/pronote/parent.html",
            "account_type": "parent",
            "username": "parent_user",
            "password": "pass",
            "session": {"token": "parent_tok"},
            "child_identifier": "guyader_sacha",
            "child_index": 0,
            "child_name": "GUYADER Sacha",
        },
        version=1,
    )
    parent_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=parent_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=1),
        ),
    ):
        await hass.config_entries.async_setup(parent_entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    devices = list(device_registry.devices.values())
    assert len(devices) == 1
    assert devices[0].model == "504"


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
