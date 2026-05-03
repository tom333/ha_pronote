"""Smoke tests for the HA-Pronote package skeleton."""

from __future__ import annotations

from custom_components.ha_pronote import DOMAIN
from custom_components.ha_pronote.const import DOMAIN as DOMAIN_CONST


def test_domain_constant_is_ha_pronote() -> None:
    """The package's DOMAIN constant must equal the manifest.domain value.

    If this assertion fails, hassfest will reject the integration because
    ``manifest.json:domain`` no longer matches the directory name.
    """
    assert DOMAIN == "ha_pronote"
    assert DOMAIN_CONST == DOMAIN


async def test_config_flow_placeholder_aborts(hass) -> None:
    """The Phase 1 placeholder Config Flow must abort cleanly.

    Once Phase 3 ships the real flow, this test will need to be replaced.
    Until then, it documents the contract: clicking "Add Integration" returns
    an abort, never a stack trace.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "abort"
    assert result["reason"] == "not_implemented"
