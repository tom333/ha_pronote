"""Config flow placeholder for HA-Pronote.

Phase 1 ships a placeholder so hassfest accepts ``config_flow: true`` in
manifest.json. The real flow lands in Phase 3 (AUTH-01, AUTH-02). Until then,
the user clicking "Add Integration" gets a clean "not yet implemented" message
rather than a broken UI.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class HaPronoteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Placeholder config flow — real implementation in Phase 3."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Reject user-initiated setup until Phase 3 ships the real flow."""
        return self.async_abort(reason="not_implemented")
