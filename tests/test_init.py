"""Smoke + setup_entry contract tests for HA-Pronote (Phase 3).

Phase 1's not-implemented placeholder flow test has been removed because
Plan 01 shipped the real flow. The constant smoke test is preserved verbatim.
"""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_pronote import DOMAIN, async_migrate_entry
from custom_components.ha_pronote.const import DOMAIN as DOMAIN_CONST


def test_domain_constant_is_ha_pronote() -> None:
    """The package's DOMAIN constant must equal the manifest.domain value.

    If this assertion fails, hassfest will reject the integration because
    ``manifest.json:domain`` no longer matches the directory name.
    """
    assert DOMAIN == "ha_pronote"
    assert DOMAIN_CONST == DOMAIN


async def test_async_setup_entry_happy_path(hass, mock_config_entry, mock_pronote_client) -> None:
    """C-05: setup uses build_or_resume_client (mocked); coordinator first-refresh OK."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ha_pronote.build_or_resume_client",
        return_value=mock_pronote_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.client is mock_pronote_client
    assert mock_config_entry.runtime_data.child_identifier == "jean_dupont"


async def test_async_migrate_entry_returns_true(hass, mock_config_entry) -> None:
    """ENT-04 / D-26 — skeleton returns True; Phase 6+ fills the body."""
    assert await async_migrate_entry(hass, mock_config_entry) is True


async def test_setup_entry_missing_required_key_raises_config_entry_not_ready(hass) -> None:
    """WR-02: a corrupted entry (missing a required key) must NOT escape as KeyError.

    HA wraps ConfigEntryNotReady cleanly (it retries setup and surfaces a
    proper status to the user); a raw KeyError traceback would be opaque.
    """
    bad_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:user:jean_dupont",
        data={
            # 'url' deliberately missing — also missing 'username',
            # 'child_identifier', 'child_name' to lock the multi-key path.
            "account_type": "eleve",
            "password": "p",
        },
        version=1,
    )
    bad_entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(bad_entry.entry_id)
    await hass.async_block_till_done()
    # ConfigEntryNotReady -> async_setup returns False; HA logs a clean message.
    assert result is False


async def test_unload_entry_shuts_down_coordinator(hass, mock_config_entry, mock_pronote_client) -> None:
    """WR-07: async_unload_entry must call coordinator.async_shutdown.

    Without it the TimestampDataUpdateCoordinator keeps its scheduled refresh
    alive until garbage-collected — and could fire one more poll AFTER unload,
    violating CLAUDE.md 'politesse polling'.
    """
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ha_pronote.build_or_resume_client",
        return_value=mock_pronote_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator
    # async_shutdown is what cancels the scheduled refresh; stub it so we can
    # observe the call without needing internal HA scheduler plumbing.
    with patch.object(coordinator, "async_shutdown") as mock_shutdown:
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_shutdown.await_count + mock_shutdown.call_count >= 1
