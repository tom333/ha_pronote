"""Real Config Flow for HA-Pronote (D-01..D-05, D-10..D-13).

D-01: single-step ``async_step_user`` form -- URL + account_type + username + password.
      `build_client(...)` is awaited via ``hass.async_add_executor_job(partial(...))``.
      eleve OR parent-with-1-child -> direct entry creation.
      parent-with-multiple-children -> ``async_step_pick_child``.
D-02: ``async_step_pick_child`` -- single-select dropdown of ``client.children``.
D-03: URL validation = ``TextSelector(type=URL)`` only (no HEAD probe; pronotepy connect
      failure is the reachability signal). The HA frontend enforces URL format via the
      selector; ``voluptuous.Url()`` cannot be JSON-serialised for the config flow UI.
D-04: error mapping (form-level errors dict -- never raises into the UI):
        AuthError              -> errors={"base": "invalid_auth"}
        RateLimitedError       -> errors={"base": "ip_suspended"}
        CommunicationError     -> errors={"base": "cannot_connect"}
        PronoteIntegrationError-> errors={"base": "unknown"}
D-05: ConfigEntry unique_id == f"{url_host.lower()}:{username}:{child_identifier}".
      Computed via urllib.parse.urlparse(url).hostname.
D-10/D-11/D-13: child_identifier = slugify(child_name, separator="_"); FROZEN at flow time;
      stored verbatim in entry.data["child_identifier"]; never re-derived later.
D-12: collision suffix -- Phase 3 ships the precheck; if the slug would collide
      with an existing entry's child_identifier on this HA install, append the
      first 2 hex chars of pronotepy.children[idx].identifier (e.g. jean_dupont_a3).

Banned in this file (CLAUDE.md "What NOT to Use" + Phase 1 D-30..D-35):
- No ``requests`` calls.
- No synchronous pronotepy calls without ``async_add_executor_job`` (Pitfall 6).
- No HEAD probe before auth (D-03 explicitly rejects).
- No hardcoded URL -- every URL comes from ``user_input["url"]``.
"""

from __future__ import annotations

from functools import partial
from typing import Any
from urllib.parse import urlparse

import pronotepy
from slugify import slugify
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import build_client, set_active_child
from .const import DOMAIN

_USER_SCHEMA = vol.Schema(
    {
        # D-03: URL validation via TextSelector(URL) — vol.Url() cannot be
        # JSON-serialised by HA's config flow result preparer (ValueError:
        # "Unable to convert schema: <function Url>"), so the URL format
        # check moves to the frontend selector. pronotepy.Client(url, ...)
        # remains the authoritative reachability + correctness signal.
        vol.Required("url"): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required("account_type"): vol.In(["eleve", "parent"]),
        vol.Required("username"): str,
        # CR-01: password rendered as masked input in HA frontend.
        vol.Required("password"): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)


class HaPronoteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Real flow -- D-01 user step, optional D-02 pick_child step."""

    VERSION = 1

    def __init__(self) -> None:
        """Stash inter-step state -- pronotepy client + last user_input."""
        self._client: pronotepy.Client | pronotepy.ParentClient | None = None
        self._user_input: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Single-step credential form per D-01.

        DEBUG MODE: typed exception mapping (D-04: AuthError → invalid_auth, etc.)
        is intentionally REMOVED so all exceptions propagate raw to HA's
        framework. This surfaces the full traceback in `ha core logs` and a
        500 in the UI instead of polite form-error labels. Re-introduce the
        mapping once the underlying pronotepy 2.14.6 vs Pronote 2025.2.9
        integration is stabilised.
        """
        if user_input is not None:
            client = await self.hass.async_add_executor_job(
                partial(
                    build_client,
                    user_input["url"],
                    user_input["account_type"],
                    user_input["username"],
                    user_input["password"],
                )
            )
            self._client = client
            self._user_input = user_input
            # D-01: parent with >1 children -> pick_child; otherwise create.
            if isinstance(client, pronotepy.ParentClient) and len(client.children) > 1:
                return await self.async_step_pick_child()
            return await self._create_entry(child_index=None)

        return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA)

    async def async_step_pick_child(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """D-02: single-select dropdown of ParentClient.children."""
        if self._client is None or not isinstance(self._client, pronotepy.ParentClient):
            # Defensive: pick_child reached without a parent client is a bug.
            return self.async_abort(reason="unknown")

        children = self._client.children

        if user_input is not None:
            return await self._create_entry(child_index=int(user_input["child_index"]))

        schema = vol.Schema(
            {vol.Required("child_index"): vol.In({str(i): child.name for i, child in enumerate(children)})}
        )
        return self.async_show_form(step_id="pick_child", data_schema=schema)

    async def _create_entry(self, child_index: int | None) -> ConfigFlowResult:
        """Resolve child, derive identifier, set unique_id, create entry.

        DEBUG MODE: every WR-06 typed catch removed — set_active_child,
        export_credentials, and child access all propagate raw exceptions.
        """
        if self._client is None or self._user_input is None:
            return self.async_abort(reason="unknown")

        if isinstance(self._client, pronotepy.ParentClient):
            if child_index is None:
                # parent with exactly one child -- implicit pick.
                child_index = 0
            await self.hass.async_add_executor_job(set_active_child, self._client, child_index)
            child = self._client.children[child_index]
            child_name = child.name
            child_pronote_identifier = child.identifier
        else:
            child_name = self._client.info.name
            child_pronote_identifier = ""  # eleve: no separate identifier

        base_slug = slugify(
            child_name, separator="_"
        )  # D-10 -- underscore separator (locks D-10/D-12/D-13 example slugs jean_dupont, alice_dupont)

        # D-12 collision precheck: scan existing entries on this HA install for
        # the same child_identifier value. If a collision is found, append the
        # first 2 hex chars of the pronotepy child identifier.
        existing_slugs = {
            entry.data.get("child_identifier") for entry in self.hass.config_entries.async_entries(DOMAIN)
        }
        if base_slug in existing_slugs and child_pronote_identifier:
            suffix = "".join(ch for ch in child_pronote_identifier.lower() if ch in "0123456789abcdef")[:2]
            child_identifier = f"{base_slug}_{suffix}" if suffix else base_slug
        else:
            child_identifier = base_slug

        # D-05 unique_id: f"{url_host.lower()}:{username}:{child_identifier}"
        url_host = (urlparse(self._user_input["url"]).hostname or "").lower()
        unique_id = f"{url_host}:{self._user_input['username']}:{child_identifier}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # D-06: capture export_credentials() at flow time so the first
        # async_setup_entry has a session to try. Plan 02's coordinator
        # writes a fresh session after every successful poll.
        session = await self.hass.async_add_executor_job(self._client.export_credentials)

        return self.async_create_entry(
            title=f"{child_name} ({self._user_input['account_type']})",
            data={
                "url": self._user_input["url"],
                "account_type": self._user_input["account_type"],
                "username": self._user_input["username"],
                "password": self._user_input["password"],  # D-08 (kept for AUTH-04 fallback)
                "session": session,  # D-06
                "child_identifier": child_identifier,  # D-11 frozen
                "child_index": child_index,  # D-08
                "child_name": child_name,  # D-08 (DeviceInfo.name)
            },
        )
