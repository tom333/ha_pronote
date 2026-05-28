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
from .api.errors import AuthError, CommunicationError, PronoteIntegrationError, RateLimitedError
from .const import DOMAIN

# D-04 typed-exception → form-error mapping (re-introduced after Phase 3 DEBUG MODE
# per Phase 6 CONTEXT.md decision — reauth/reconfigure depend on this surface).
_ERROR_KEY_BY_EXC: tuple[tuple[type[Exception], str], ...] = (
    (AuthError, "invalid_auth"),
    (RateLimitedError, "ip_suspended"),
    (CommunicationError, "cannot_connect"),
    (PronoteIntegrationError, "unknown"),
)


def _map_error(exc: Exception) -> str:
    """Map a typed pronote integration error to the D-04 form-error key.

    Returns ``"unknown"`` for any unrecognised exception. Order matters because
    ``RateLimitedError`` subclasses ``PronoteIntegrationError`` etc. — the
    sequence above places narrower types before the catch-all.
    """
    for exc_type, key in _ERROR_KEY_BY_EXC:
        if isinstance(exc, exc_type):
            return key
    return "unknown"


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

        D-04: typed exceptions from ``build_client`` are mapped to form-error
        keys (``invalid_auth`` / ``ip_suspended`` / ``cannot_connect`` /
        ``unknown``) and the form is re-shown. Phase 6 reauth/reconfigure flows
        rely on this same mapping.
        """
        if user_input is not None:
            try:
                client = await self.hass.async_add_executor_job(
                    partial(
                        build_client,
                        user_input["url"],
                        user_input["account_type"],
                        user_input["username"],
                        user_input["password"],
                    )
                )
            except PronoteIntegrationError as err:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_USER_SCHEMA,
                    errors={"base": _map_error(err)},
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

        WR-06: typed pronote exceptions from ``set_active_child`` and
        ``export_credentials`` map to the D-04 abort reason (``invalid_auth`` /
        ``ip_suspended`` / ``cannot_connect`` / ``unknown``). A bare
        ``RuntimeError`` from ``export_credentials`` (e.g. half-init client)
        maps to ``cannot_connect`` — pronotepy occasionally leaks plain
        exceptions on partial-init paths.
        """
        if self._client is None or self._user_input is None:
            return self.async_abort(reason="unknown")

        if isinstance(self._client, pronotepy.ParentClient):
            if child_index is None:
                # parent with exactly one child -- implicit pick.
                child_index = 0
            try:
                await self.hass.async_add_executor_job(set_active_child, self._client, child_index)
            except PronoteIntegrationError as err:
                return self.async_abort(reason=_map_error(err))
            child = self._client.children[child_index]
            child_name = child.name
        else:
            child_name = self._client.info.name

        # D-10 — underscore separator slug. D-12 collision-suffix logic was
        # dropped: it relied on pronotepy `Child.identifier` which actually
        # returns a `ClientInfo` object without an `identifier` attribute on
        # this server. Reintroduce in Phase 6 once we have a live-fixture
        # script (scripts/test_config_flow.py) that inspects real pronotepy
        # output. With a single child the collision check is a no-op anyway.
        child_identifier = slugify(child_name, separator="_")

        # D-05 unique_id: f"{url_host.lower()}:{username}:{child_identifier}"
        url_host = (urlparse(self._user_input["url"]).hostname or "").lower()
        unique_id = f"{url_host}:{self._user_input['username']}:{child_identifier}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # D-06: capture export_credentials() at flow time so the first
        # async_setup_entry has a session to try. Plan 02's coordinator
        # writes a fresh session after every successful poll.
        try:
            session = await self.hass.async_add_executor_job(self._client.export_credentials)
        except PronoteIntegrationError as err:
            return self.async_abort(reason=_map_error(err))
        except RuntimeError:
            # pronotepy 2.14.6 occasionally raises a plain RuntimeError from a
            # half-initialised client (e.g. mid-recovery race). Surface as
            # cannot_connect so the user knows to retry rather than seeing an
            # opaque "unknown" abort.
            return self.async_abort(reason="cannot_connect")

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
