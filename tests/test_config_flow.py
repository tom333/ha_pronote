"""HA-side tests for the real Config Flow (D-01..D-05, ENT-02 anchor).

C-05: patch custom_components.ha_pronote.config_flow.build_client to return
a MagicMock client. This decouples HA-side tests from pronotepy internals
(which are exercised separately by tests/test_api/test_client.py via
requests-mock).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.ha_pronote.api import (
    AuthError,
    CommunicationError,
    ErrorReason,
    PronoteIntegrationError,
    RateLimitedError,
)
from custom_components.ha_pronote.config_flow import _REAUTH_SCHEMA, _USER_SCHEMA
from custom_components.ha_pronote.const import DOMAIN
from homeassistant.helpers.selector import TextSelector, TextSelectorType

_USER_INPUT_ELEVE = {
    "url": "https://example.com/pronote/eleve.html",
    "account_type": "eleve",
    "username": "alice",
    "password": "p",
}

_USER_INPUT_PARENT = {
    "url": "https://example.com/pronote/parent.html",
    "account_type": "parent",
    "username": "alice",
    "password": "p",
}


async def test_user_step_eleve_happy_path(hass, mock_pronote_client) -> None:
    """D-01: eleve account, single-step flow creates entry directly."""
    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        return_value=mock_pronote_client,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_ELEVE)
    assert result["type"] == "create_entry"
    assert result["data"]["child_identifier"] == "jean_dupont"
    assert result["data"]["account_type"] == "eleve"
    assert result["data"]["child_name"] == "Jean Dupont"


async def test_user_step_parent_two_children_transitions_to_pick_child(hass, mock_parent_client_two_children) -> None:
    """D-02: ParentClient with > 1 child triggers pick_child step."""
    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        return_value=mock_parent_client_two_children,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_PARENT)
    assert result["type"] == "form"
    assert result["step_id"] == "pick_child"


async def test_user_step_pick_child_creates_entry(hass, mock_parent_client_two_children) -> None:
    """D-02 continuation — picking child 0 creates the entry."""
    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        return_value=mock_parent_client_two_children,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_PARENT)
        # pick_child step.
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"child_index": "0"})
    assert result["type"] == "create_entry"
    assert result["data"]["child_index"] == 0
    assert result["data"]["child_identifier"] == "alice_dupont"  # slugify(child[0].name)
    # set_active_child resolves an int index → client.children[index] before delegating
    # to client.set_child (api/client.py:set_active_child). Assert the resolved Child
    # object was passed, not the bare int index.
    mock_parent_client_two_children.set_child.assert_called_once_with(mock_parent_client_two_children.children[0])


@pytest.mark.parametrize(
    ("raised", "expected_error"),
    [
        (AuthError("bad creds"), "invalid_auth"),
        (
            RateLimitedError("Your IP address is suspended"),
            "ip_suspended",
        ),
        (CommunicationError("network unreachable"), "cannot_connect"),
        (
            PronoteIntegrationError(ErrorReason.PARSE_ERROR, "weird"),
            "unknown",
        ),
    ],
)
async def test_user_step_error_mapping(hass, raised, expected_error) -> None:
    """D-04: AuthError -> invalid_auth; RateLimited -> ip_suspended; etc."""
    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        side_effect=raised,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_ELEVE)
    assert result["type"] == "form"
    assert result["errors"] == {"base": expected_error}


async def test_unique_id_format_locks_d05(hass, mock_pronote_client) -> None:
    """D-05: unique_id == f'{url_host.lower()}:{username}:{child_identifier}'."""
    with (
        patch(
            "custom_components.ha_pronote.config_flow.build_client",
            return_value=mock_pronote_client,
        ),
        patch(
            "custom_components.ha_pronote.build_or_resume_client",
            return_value=mock_pronote_client,
        ),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_ELEVE)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert any(e.unique_id == "example.com:alice:jean_dupont" for e in entries), [e.unique_id for e in entries]


async def test_already_configured_aborts(hass, mock_pronote_client) -> None:
    """D-05: second add of the same host:user:slug aborts with already_configured."""
    pre_existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:alice:jean_dupont",
        data={"placeholder": "preexisting"},
        version=1,
    )
    pre_existing.add_to_hass(hass)

    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        return_value=mock_pronote_client,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_ELEVE)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# CR-01: password field must be a TextSelector(type=PASSWORD) so the HA
# frontend masks the input.
# ---------------------------------------------------------------------------


def test_user_schema_masks_password_field() -> None:
    """CR-01: password field declared with TextSelector(type=PASSWORD)."""
    schema_dict = _USER_SCHEMA.schema
    pw_validator = next(v for k, v in schema_dict.items() if str(k) == "password")
    assert isinstance(pw_validator, TextSelector)
    assert pw_validator.config["type"] == TextSelectorType.PASSWORD


# ---------------------------------------------------------------------------
# WR-06: set_active_child / export_credentials failures in _create_entry must
# bubble through the D-04 mapping rather than escaping as 'Unknown error'.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raised", "expected_reason"),
    [
        (AuthError("session torn"), "invalid_auth"),
        (RateLimitedError("Your IP address is suspended"), "ip_suspended"),
        (CommunicationError("network down"), "cannot_connect"),
    ],
)
async def test_create_entry_set_active_child_error_aborts_with_mapped_reason(
    hass, mock_parent_client_two_children, raised, expected_reason
) -> None:
    """WR-06: pronotepy.set_child failure surfaces as the D-04 abort reason."""
    with (
        patch(
            "custom_components.ha_pronote.config_flow.build_client",
            return_value=mock_parent_client_two_children,
        ),
        patch(
            "custom_components.ha_pronote.config_flow.set_active_child",
            side_effect=raised,
        ),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_PARENT)
        # pick_child step.
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"child_index": "0"})
    assert result["type"] == "abort"
    assert result["reason"] == expected_reason


async def test_create_entry_export_credentials_failure_aborts_cannot_connect(hass, mock_pronote_client) -> None:
    """WR-06: export_credentials raising at flow time aborts with cannot_connect."""
    mock_pronote_client.export_credentials.side_effect = RuntimeError("half-init")
    with patch(
        "custom_components.ha_pronote.config_flow.build_client",
        return_value=mock_pronote_client,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input=_USER_INPUT_ELEVE)
    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


# ---------------------------------------------------------------------------
# Phase 6 — Reauth flow tests (AUTH-05, D-01..D-04).
# ---------------------------------------------------------------------------

_REAUTH_ENTRY_DATA = {
    "url": "https://example.com/pronote/eleve.html",
    "account_type": "eleve",
    "username": "alice",
    "password": "old_pw",
    "session": {"token": "old_session_blob"},
    "child_identifier": "jean_dupont",
    "child_index": None,
    "child_name": "Jean Dupont",
}


async def test_reauth_flow_happy_path(hass, mock_pronote_client) -> None:
    """AUTH-05 / D-01 / D-02 / D-03 — new password persisted, session cleared, URL preserved."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:alice:jean_dupont",
        data=_REAUTH_ENTRY_DATA,
        version=1,
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.ha_pronote.config_flow.build_or_resume_client",
        return_value=mock_pronote_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"username": "alice", "password": "new_pw"},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    # D-02 — session cleared:
    assert entry.data["session"] is None
    # D-01 — username + password updated:
    assert entry.data["username"] == "alice"
    assert entry.data["password"] == "new_pw"
    # RESEARCH Pitfall #6 — merge, not replace: url/account_type/child_* preserved:
    assert entry.data["url"] == _REAUTH_ENTRY_DATA["url"]
    assert entry.data["account_type"] == "eleve"
    assert entry.data["child_identifier"] == "jean_dupont"
    assert entry.data["child_name"] == "Jean Dupont"
    assert entry.data["child_index"] is None


@pytest.mark.parametrize(
    ("raised", "expected_error"),
    [
        (AuthError("bad creds"), "invalid_auth"),
        (
            RateLimitedError("Your IP address is suspended"),
            "ip_suspended",
        ),
        (CommunicationError("network unreachable"), "cannot_connect"),
        (
            PronoteIntegrationError(ErrorReason.PARSE_ERROR, "weird"),
            "unknown",
        ),
    ],
)
async def test_reauth_error_mapping(hass, raised, expected_error) -> None:
    """AUTH-05 D-04 — typed exceptions surface as form-error keys; entry.data UNCHANGED on error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:alice:jean_dupont",
        data=_REAUTH_ENTRY_DATA,
        version=1,
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.ha_pronote.config_flow.build_or_resume_client",
        side_effect=raised,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"username": "alice", "password": "p"},
        )
    assert result["type"] == "form"
    assert result["errors"] == {"base": expected_error}
    # Entry data MUST be untouched on error.
    assert entry.data["password"] == "old_pw"
    assert entry.data["session"] == {"token": "old_session_blob"}


async def test_reauth_updates_username_and_password(hass, mock_pronote_client) -> None:
    """D-01 — username CAN be edited at reauth (broader than AUTH-05's strict reading)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="example.com:alice:jean_dupont",
        data=_REAUTH_ENTRY_DATA,
        version=1,
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.ha_pronote.config_flow.build_or_resume_client",
        return_value=mock_pronote_client,
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"username": "alice_renamed", "password": "new_pw"},
        )

    assert entry.data["username"] == "alice_renamed"
    assert entry.data["password"] == "new_pw"


def test_reauth_schema_masks_password_field() -> None:
    """D-01 / CR-01 mirror — reauth password field is TextSelector(PASSWORD)."""
    password_validator = _REAUTH_SCHEMA.schema[vol.Required("password")]
    assert isinstance(password_validator, TextSelector)
    # The selector config carries type=password — assert via its config attribute.
    # Brittle: accesses TextSelector internal config dict. Mirrors Phase 3
    # test_user_schema_masks_password_field; replace both if HA Core changes
    # selector internals.
    assert password_validator.config["type"] == TextSelectorType.PASSWORD.value
