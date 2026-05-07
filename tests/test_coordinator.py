"""HA-side tests for PronoteDataUpdateCoordinator (D-06, D-09, D-19, D-22, COORD-02)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from custom_components.ha_pronote.api import AuthError, CommunicationError, RateLimitedError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed


async def test_first_refresh_writes_session_to_entry_data(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-06: coordinator captures export_credentials() after a successful poll."""
    today = date(2026, 5, 7)
    mock_pronote_client.export_credentials.return_value = {"token": "fresh_token"}
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
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert mock_config_entry.data["session"] == {"token": "fresh_token"}


async def test_coordinator_data_is_snapshot(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-20: coordinator.data: Snapshot directly (no extra wrapper)."""
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
    assert coordinator.data is not None
    assert hasattr(coordinator.data, "lessons_today")  # Snapshot duck-typing


async def test_auth_error_during_setup_aborts_setup(hass, mock_config_entry) -> None:
    """D-22: AuthError during async_config_entry_first_refresh -> setup fails cleanly."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ha_pronote.build_or_resume_client",
        side_effect=AuthError("bad creds"),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    # async_setup_entry raises ConfigEntryAuthFailed -> HA marks setup failed.
    assert result is False


async def test_rate_limited_during_poll_raises_update_failed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-22: RateLimitedError -> UpdateFailed (Phase 5 reads .reason for backoff)."""
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

    coordinator = mock_config_entry.runtime_data.coordinator
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=RateLimitedError("Your IP address is suspended"),
        ),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_communication_error_during_poll_raises_update_failed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-22: CommunicationError -> UpdateFailed."""
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

    coordinator = mock_config_entry.runtime_data.coordinator
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=CommunicationError("network down"),
        ),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_no_blocking_calls_during_poll(
    hass,
    caplog,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """COORD-02 / ROADMAP SC#3: every pronotepy call wrapped in async_add_executor_job.

    HA's blocking-call detector logs "Detected blocking call" if a sync I/O call
    escapes the executor boundary. This test asserts the log is clean over a poll.
    """
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
    assert "Detected blocking call" not in caplog.text


async def test_update_interval_is_30_minutes(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """D-24: hardcoded 30-min cadence; Phase 5 makes it adaptive."""
    today = date(2026, 5, 7)
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot_with_n_lessons_today(today, n=0),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator.update_interval == timedelta(minutes=30)


async def test_previous_snapshot_populated_after_first_refresh(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """C-03: coordinator stashes previous snapshot for Phase 4's diff layer."""
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
    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator._previous_snapshot is not None  # noqa: SLF001
    assert hasattr(coordinator._previous_snapshot, "lessons_today")  # noqa: SLF001


# ---------------------------------------------------------------------------
# CR-02: _recover_from_auth_error must raise UpdateFailed (NOT
# ConfigEntryAuthFailed) when the retry's fetch_all raises RateLimitedError or
# CommunicationError. Only a real second AuthError is a genuine auth failure.
# ---------------------------------------------------------------------------


async def _setup_coordinator(hass, mock_config_entry, mock_pronote_client, snapshot, today):
    """Boot the integration with a happy first refresh; return the coordinator."""
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            return_value=snapshot,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry.runtime_data.coordinator


async def test_recovery_rate_limited_raises_update_failed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """CR-02: retry fetch raises RateLimitedError -> UpdateFailed (NOT auth-failed)."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                RateLimitedError("Your IP address is suspended"),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_recovery_network_error_raises_update_failed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """CR-02: retry fetch raises CommunicationError -> UpdateFailed (NOT auth-failed)."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                CommunicationError("network down"),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001


async def test_recovery_auth_failed_again_raises_config_entry_auth_failed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """CR-02: retry fetch raises AuthError again -> ConfigEntryAuthFailed (HA reauth)."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                AuthError("credentials really invalid"),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001
