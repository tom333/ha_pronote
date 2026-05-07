"""HA cloud-polling coordinator. Wraps api/fetcher.fetch_all in executor (D-19, COORD-01).

D-19: TimestampDataUpdateCoordinator subclass — gives last_update_success_time
      for free (Phase 4's diff layer reads it).
D-20: coordinator.data: Snapshot directly (no extra wrapper).
D-22: AuthError -> ConfigEntryAuthFailed; RateLimitedError(IP_SUSPENDED) -> UpdateFailed;
      CommunicationError / other -> UpdateFailed.
D-23: school_tz from PronoteData; today via dt_util.now(school_tz).date().
D-24: update_interval = const.DEFAULT_REFRESH_INTERVAL (30 min hardcoded; Phase 5 adapts).
D-06: client.export_credentials() captured AFTER every successful poll, written
      to entry.data['session'] via async_update_entry.
D-09: mid-poll AuthError -> single fresh re-login + retry; second failure ->
      ConfigEntryAuthFailed (HA fires reauth — Phase 6).
C-03: previous Snapshot stashed on self._previous_snapshot (Phase 4 reads).

Banned (CLAUDE.md "What NOT to Use" + Phase 1 D-30..D-35):
- No legacy timeout helper (use ``asyncio.timeout`` if needed — not needed here).
- No pytz (zoneinfo.ZoneInfo only).
- No direct requests (pronotepy via executor only).
- No storing pronotepy.Client in coordinator.data (Anti-Pattern 7) — the live
  client lives on entry.runtime_data.client (D-21) AND on self._client (mutable
  for D-09 silent recovery).
"""

from __future__ import annotations

from functools import partial
import logging
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import (
    AuthError,
    CommunicationError,
    PronoteIntegrationError,
    RateLimitedError,
    fetch_all,
    redact,
    set_active_child,
)
from .api.client import build_or_resume_client
from .const import DEFAULT_REFRESH_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from datetime import date
    from zoneinfo import ZoneInfo

    import pronotepy

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api.models import Snapshot


_LOGGER = logging.getLogger(__name__)


class PronoteDataUpdateCoordinator(TimestampDataUpdateCoordinator["Snapshot"]):
    """One coordinator per ConfigEntry. Polls Pronote on a 30-min cadence (D-19, D-24)."""

    def __init__(  # noqa: PLR0913 — coordinator wires entry + client + child + tz from __init__.py
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: pronotepy.Client | pronotepy.ParentClient,
        child_identifier: str,
        child_index: int | None,
        school_tz: ZoneInfo,
    ) -> None:
        """Initialize with a live pronotepy client (built by __init__.py:async_setup_entry)."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{child_identifier}",
            update_interval=DEFAULT_REFRESH_INTERVAL,
            config_entry=entry,
        )
        self._client = client  # live, between polls (D-21)
        self._child_identifier = child_identifier  # frozen at flow time (D-11)
        self._child_index = child_index  # for ParentClient.set_child (D-08)
        self._school_tz = school_tz  # D-23
        self._previous_snapshot: Snapshot | None = None  # C-03 — Phase 4 reads

    async def _async_update_data(self) -> Snapshot:
        """Fetch a Snapshot via executor; capture session token on success (D-19)."""
        today = dt_util.now(self._school_tz).date()  # D-23 — coordinator owns dt_util
        try:
            snapshot = await self.hass.async_add_executor_job(
                partial(
                    fetch_all,
                    self._client,
                    today,
                    self._school_tz,
                    self._child_index,
                )
            )
        except AuthError as err:
            # D-09 — silent recovery: try ONE fresh re-login + retry the fetch.
            snapshot = await self._recover_from_auth_error(err, today)
        except RateLimitedError as err:
            # D-22 — IP_SUSPENDED -> UpdateFailed; Phase 5 reads .reason for backoff.
            raise UpdateFailed(f"[{err.reason}] {redact(err.message)}") from err  # WR-05
        except (CommunicationError, PronoteIntegrationError) as err:
            raise UpdateFailed(f"[{err.reason}] {redact(err.message)}") from err  # WR-05

        await self._capture_session()  # D-06
        self._previous_snapshot = snapshot  # C-03
        return snapshot

    async def _recover_from_auth_error(
        self,
        original_err: AuthError,
        today: date,
    ) -> Snapshot:
        """D-09: single fresh re-login + retry; on second failure raise ConfigEntryAuthFailed."""
        entry = self.config_entry
        if entry is None:
            raise ConfigEntryAuthFailed(str(original_err)) from original_err

        try:
            new_client = await self.hass.async_add_executor_job(
                partial(
                    build_or_resume_client,
                    entry.data["url"],
                    entry.data["account_type"],
                    entry.data["username"],
                    entry.data["password"],
                    None,  # force fresh login (skip token_login fast path)
                    f"home-assistant-{entry.entry_id[:8]}",  # AUTH-07 (D-18, C-04)
                )
            )
            # ParentClient: re-apply the chosen child before fetch.
            # CR-04: set_active_child wraps client.set_child with typed-error
            # mapping so a CryptoError on this call surfaces as AuthError (caught
            # by the existing except arm below) instead of leaking pronotepy.
            if self._child_index is not None and hasattr(new_client, "set_child"):
                await self.hass.async_add_executor_job(set_active_child, new_client, self._child_index)
            self._client = new_client
            snapshot = await self.hass.async_add_executor_job(
                partial(
                    fetch_all,
                    self._client,
                    today,
                    self._school_tz,
                    self._child_index,
                )
            )
        # CR-02: D-22 mandates AuthError -> ConfigEntryAuthFailed (HA reauth) but
        # RateLimitedError / CommunicationError -> UpdateFailed (HA retries on
        # the next poll). The previous catch-all on PronoteIntegrationError
        # mis-classified IP_SUSPENDED and transient network blips as auth
        # failures, triggering spurious reauth flows and discarding the
        # circuit-breaker signal Phase 5 needs.
        except AuthError as err:
            # Real auth failure on the retry — credentials genuinely invalid.
            raise ConfigEntryAuthFailed(f"[{err.reason}] {redact(err.message)}") from err
        except RateLimitedError as err:
            # IP suspended during recovery — Phase 5's circuit-breaker reads .reason.
            raise UpdateFailed(f"[{err.reason}] {redact(err.message)}") from err
        except (CommunicationError, PronoteIntegrationError) as err:
            # Transient — HA retries on next poll.
            raise UpdateFailed(f"[{err.reason}] {redact(err.message)}") from err

        return snapshot

    async def _capture_session(self) -> None:
        """D-06: call client.export_credentials() in executor, write to entry.data."""
        entry = self.config_entry
        if entry is None:
            return
        new_session = await self.hass.async_add_executor_job(self._client.export_credentials)
        if new_session != entry.data.get("session"):
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, "session": new_session})
