"""Token persistence round-trip — D-06, D-07, D-09 (AUTH-04, AUTH-07)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pronotepy
import pytest

from custom_components.ha_pronote.api import AuthError, RateLimitedError
from custom_components.ha_pronote.api.client import build_or_resume_client


def test_build_or_resume_client_uses_token_login_when_session_present(monkeypatch):
    """D-07 fast path — token_login first when session is non-None; passes device_name."""
    captured: dict = {}

    def _token_login(cls, url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return MagicMock(spec=pronotepy.Client)

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))

    client = build_or_resume_client(
        "https://example.com/pronote/eleve.html",
        "eleve",
        "u",
        "p",
        session={"token": "abc"},
        device_name="home-assistant-12345678",
    )
    assert client is not None
    assert captured.get("device_name") == "home-assistant-12345678"
    assert captured.get("token") == "abc"
    assert captured.get("username") == "u"


def test_build_or_resume_client_falls_back_on_crypto_error(monkeypatch):
    """D-07 — token_login raises CryptoError -> fresh Client(...) is called."""

    def _token_login(cls, *_a, **_kw):
        raise pronotepy.exceptions.CryptoError("Padding error")

    fresh_init_kwargs: dict = {}

    def _fresh_init(self, *_args, **kwargs):
        fresh_init_kwargs.update(kwargs)

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    client = build_or_resume_client(
        "https://example.com/pronote/eleve.html",
        "eleve",
        "u",
        "p",
        session={"token": "stale"},
        device_name="home-assistant-deadbeef",
    )
    assert client is not None
    assert fresh_init_kwargs.get("device_name") == "home-assistant-deadbeef"


def test_build_or_resume_client_falls_back_on_pronote_api_error(monkeypatch):
    """D-07 — token_login raises PronoteAPIError -> fresh login."""

    def _token_login(cls, *_a, **_kw):
        raise pronotepy.PronoteAPIError("session expired")

    def _fresh_init(self, *_args, **_kw):
        return None

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    client = build_or_resume_client(
        "https://example.com/pronote/eleve.html",
        "eleve",
        "u",
        "p",
        session={"token": "stale"},
        device_name="home-assistant-deadbeef",
    )
    assert client is not None


def test_build_or_resume_client_falls_back_on_os_error(monkeypatch):
    """D-07 — token_login raises OSError -> fresh login attempted."""

    def _token_login(cls, *_a, **_kw):
        raise OSError("transient")

    def _fresh_init(self, *_args, **_kw):
        return None

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    client = build_or_resume_client(
        "https://example.com/pronote/eleve.html",
        "eleve",
        "u",
        "p",
        session={"token": "stale"},
        device_name="home-assistant-deadbeef",
    )
    assert client is not None


def test_build_or_resume_client_no_session_takes_fresh_path(monkeypatch):
    """D-07 — session=None means token_login is NEVER invoked."""

    def _token_login(cls, *_a, **_kw):
        pytest.fail("token_login must NOT be called when session is None")

    def _fresh_init(self, *_args, **_kw):
        return None

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    client = build_or_resume_client(
        "https://example.com/pronote/eleve.html",
        "eleve",
        "u",
        "p",
        session=None,
        device_name="home-assistant-deadbeef",
    )
    assert client is not None


def test_fresh_login_crypto_error_raises_auth_error(monkeypatch):
    """D-07 fallback path — fresh login CryptoError -> AuthError."""

    def _token_login(cls, *_a, **_kw):
        raise pronotepy.exceptions.CryptoError("token bad")

    def _fresh_init(self, *_args, **_kw):
        raise pronotepy.exceptions.CryptoError("password bad")

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    with pytest.raises(AuthError):
        build_or_resume_client(
            "https://example.com/pronote/eleve.html",
            "eleve",
            "u",
            "p",
            session={"token": "stale"},
            device_name="home-assistant-deadbeef",
        )


def test_fresh_login_ip_suspended_raises_rate_limited(monkeypatch):
    """D-07 fallback path — fresh login PronoteAPIError 'IP suspended' -> RateLimitedError."""

    def _token_login(cls, *_a, **_kw):
        raise pronotepy.PronoteAPIError("token gone")

    def _fresh_init(self, *_args, **_kw):
        raise pronotepy.PronoteAPIError("Your IP address is suspended for 24h")

    monkeypatch.setattr(pronotepy.Client, "token_login", classmethod(_token_login))
    monkeypatch.setattr(pronotepy.Client, "__init__", _fresh_init)

    with pytest.raises(RateLimitedError):
        build_or_resume_client(
            "https://example.com/pronote/eleve.html",
            "eleve",
            "u",
            "p",
            session={"token": "stale"},
            device_name="home-assistant-deadbeef",
        )


async def test_coordinator_writes_new_session_after_silent_recovery(
    hass, mock_config_entry, mock_pronote_client, snapshot_with_n_lessons_today
) -> None:
    """D-09 — mid-poll AuthError -> single fresh re-login -> new session captured to entry.data."""
    today = date(2026, 5, 7)
    fresh_client = MagicMock()
    fresh_client.export_credentials = MagicMock(return_value={"token": "post_recovery"})
    fresh_client.set_child = MagicMock()

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

    # Now poke a mid-poll AuthError; recovery rebuilds client + retries fetch.
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
        await coordinator.async_refresh()

    assert mock_config_entry.data["session"] == {"token": "post_recovery"}
