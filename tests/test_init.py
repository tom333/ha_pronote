"""Smoke + setup_entry contract tests for HA-Pronote (Phase 3).

Phase 1's not-implemented placeholder flow test has been removed because
Plan 01 shipped the real flow. The constant smoke test is preserved verbatim.
"""

from __future__ import annotations

from unittest.mock import patch

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
