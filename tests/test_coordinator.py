"""HA-side tests for PronoteDataUpdateCoordinator (D-06, D-09, D-19, D-22, COORD-02)."""

from __future__ import annotations

from datetime import date, timedelta
import time
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
) -> None:
    """COORD-02 / ROADMAP SC#3: every pronotepy call wrapped in async_add_executor_job.

    WR-08: this test used to patch ``fetch_all`` AWAY, so HA's blocking-call
    detector had nothing to catch — the assertion was trivially true regardless
    of whether the production code actually wrapped the calls in the executor.
    The fix: let the real ``fetch_all`` execute against ``mock_pronote_client``,
    whose ``.lessons()`` / ``.information_and_surveys()`` methods perform a
    genuine ``time.sleep(0.001)`` (a real blocking call). HA's detector
    triggers ONLY on real sync I/O on the event loop thread; if the production
    code's ``async_add_executor_job`` wrapping is correct, those sleeps run
    on an executor thread and the loop-thread detector stays silent.

    If anyone removes the ``async_add_executor_job`` wrap in
    ``coordinator._async_update_data`` or ``api.fetcher.fetch_all``, this
    test will surface a "Detected blocking call to sleep" log entry.
    """
    today = date(2026, 5, 7)

    # Make the mock client's IO methods perform an actual blocking sleep.
    # When fetch_all runs on the event loop thread (broken contract), HA's
    # detector logs "Detected blocking call to sleep". When fetch_all runs in
    # the executor (correct contract), the detector stays silent.
    def _blocking_lessons(*_args, **_kwargs):
        time.sleep(0.001)
        return []

    def _blocking_info(*_args, **_kwargs):
        time.sleep(0.001)
        return []

    mock_pronote_client.lessons = _blocking_lessons
    mock_pronote_client.information_and_surveys = _blocking_info
    # current_period.grades is read as an attribute, not called — leave as [].

    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ha_pronote.build_or_resume_client",
        return_value=mock_pronote_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    # Reference today so ruff doesn't flag the variable as unused.
    assert today.year == 2026
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


# ---------------------------------------------------------------------------
# CR-03 / CR-05: a token-write failure must NOT invalidate a successful poll.
# ---------------------------------------------------------------------------


async def test_export_credentials_failure_does_not_invalidate_poll(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """CR-03 / CR-05: export_credentials() raises -> poll still succeeds.

    The freshly-fetched snapshot must land on coordinator.data,
    last_update_success must be True, and _previous_snapshot must be updated
    so Phase 4's diff baseline stays in sync.
    """
    today = date(2026, 5, 7)
    snapshot = snapshot_with_n_lessons_today(today, n=2)
    mock_pronote_client.export_credentials.side_effect = RuntimeError("transient export failure")

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

    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator.last_update_success is True
    assert coordinator.data is snapshot
    assert coordinator._previous_snapshot is snapshot  # noqa: SLF001 — C-03 baseline locked


# ---------------------------------------------------------------------------
# WR-04: silent recovery is gated by a 5-minute cooldown so an aliased AuthError
# loop does NOT issue a fresh-login HTTP request to the same banned IP every
# poll.
# ---------------------------------------------------------------------------


async def test_recovery_cooldown_skips_back_to_back_auth_errors(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """WR-04: a second AuthError within the cooldown window must NOT re-login."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    # First recovery: AuthError on initial fetch -> recovery rebuilds client
    # and the retry succeeds. _last_recovery_at is now set.
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                snapshot_with_n_lessons_today(today, n=2),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ) as mock_build,
    ):
        await coordinator._async_update_data()  # noqa: SLF001
        assert mock_build.call_count == 1

    # Second poll, also AuthError, within the 5-minute cooldown: recovery
    # path MUST short-circuit to UpdateFailed without invoking
    # build_or_resume_client a second time.
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=AuthError("aliased rate-limit"),
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ) as mock_build,
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()  # noqa: SLF001
        assert mock_build.call_count == 0, "WR-04: must NOT issue a recovery login during cooldown"


# ---------------------------------------------------------------------------
# WR-09: a SUCCESSFUL silent recovery clears the cooldown so a subsequent
# genuine auth failure within the 5-minute window is NOT swallowed. WR-04's
# cooldown is meant to block aliased-AuthError loops (Pitfall 2), not real
# credential rotations that happen to land within 5 minutes of a prior
# session expiry.
# ---------------------------------------------------------------------------


async def test_successful_recovery_clears_cooldown(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """WR-09: after _recover_from_auth_error succeeds, _last_recovery_at must
    be cleared so the cooldown gate does not block a subsequent genuine
    AuthError. Without the clear, a real password rotation within 5 minutes
    of a session expiry would silently UpdateFailed instead of triggering
    reauth via ConfigEntryAuthFailed."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    # Drive a recovery path: AuthError on initial fetch, retry succeeds.
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                snapshot_with_n_lessons_today(today, n=2),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ),
    ):
        await coordinator._async_update_data()  # noqa: SLF001

    # WR-09: the success path MUST clear the cooldown timestamp.
    assert coordinator._last_recovery_at is None, (  # noqa: SLF001
        "WR-09: successful recovery must clear _last_recovery_at"
    )


async def test_genuine_auth_failure_after_successful_recovery_is_not_swallowed(
    hass,
    mock_config_entry,
    mock_pronote_client,
    snapshot_with_n_lessons_today,
) -> None:
    """WR-09: a SECOND AuthError that lands within 5 minutes of a successful
    recovery (e.g. user actually rotated their Pronote password) MUST trigger
    a fresh recovery attempt — not be swallowed by the cooldown gate. The
    behavioural proof: build_or_resume_client IS called a second time, and
    the genuine auth-failed retry surfaces ConfigEntryAuthFailed (HA reauth)
    rather than UpdateFailed (silent skip)."""
    today = date(2026, 5, 7)
    coordinator = await _setup_coordinator(
        hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today(today, n=1), today
    )

    fresh_client = MagicMock()
    fresh_client.set_child = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "x"})

    # Poll N: AuthError -> recovery succeeds (cooldown should be cleared).
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("session expired"),
                snapshot_with_n_lessons_today(today, n=2),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ) as mock_build_n,
    ):
        await coordinator._async_update_data()  # noqa: SLF001
        assert mock_build_n.call_count == 1

    # Poll N+1 (immediately after): AuthError + retry-AuthError ->
    # ConfigEntryAuthFailed. Without WR-09's clear, the cooldown would
    # short-circuit to UpdateFailed before recovery even started, hiding the
    # genuine credential failure from HA's reauth flow.
    with (
        patch(
            "custom_components.ha_pronote.coordinator.fetch_all",
            side_effect=[
                AuthError("credentials rotated"),
                AuthError("credentials still bad"),
            ],
        ),
        patch(
            "custom_components.ha_pronote.coordinator.build_or_resume_client",
            return_value=fresh_client,
        ) as mock_build_n_plus_1,
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()  # noqa: SLF001

    assert mock_build_n_plus_1.call_count == 1, (
        "WR-09: cleared cooldown must allow a fresh recovery attempt — "
        "build_or_resume_client should be called once for the second AuthError"
    )
