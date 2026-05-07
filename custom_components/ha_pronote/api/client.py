"""Sync facade over pronotepy. HA-free per D-19/D-20.

Caller (Phase 3 coordinator) wraps each call in ``hass.async_add_executor_job(partial(...))``.
"""

from __future__ import annotations

from typing import Any, Literal

import pronotepy

from .errors import AuthError, CommunicationError, ErrorReason, RateLimitedError, redact

AccountType = Literal["eleve", "parent"]

_IP_SUSPENDED_LITERAL = "Your IP address is suspended"  # D-22, Pitfall 1


def build_client(
    url: str,
    account_type: AccountType,
    username: str,
    password: str,
) -> pronotepy.Client | pronotepy.ParentClient:
    """Construct a pronotepy client (D-21).

    Args:
        url: Full Pronote space URL (e.g. ``https://example.com/pronote/eleve.html``).
            Phase 1 D-34: never hardcoded — caller passes from ConfigEntry data.
        account_type: ``"eleve"`` or ``"parent"`` (C-04).
        username: Pronote account username.
        password: Pronote account password.

    Returns:
        ``pronotepy.Client`` for ``"eleve"``, ``pronotepy.ParentClient`` for ``"parent"``.

    Raises:
        AuthError: pronotepy ``CryptoError`` or auth-shaped failure (Pitfall 2).
        RateLimitedError: pronotepy returned the literal "Your IP address is
            suspended" (Pitfall 1, D-22).
        CommunicationError: any other pronotepy or network failure.
    """
    cls: type[pronotepy.Client | pronotepy.ParentClient]
    cls = pronotepy.ParentClient if account_type == "parent" else pronotepy.Client
    try:
        return cls(url, username=username, password=password)
    except pronotepy.exceptions.CryptoError as err:
        raise AuthError(redact(str(err))) from err  # WR-05
    except pronotepy.PronoteAPIError as err:
        msg = redact(str(err))  # WR-05
        if _IP_SUSPENDED_LITERAL in str(err):
            raise RateLimitedError(msg) from err
        raise CommunicationError(
            msg,
            reason=ErrorReason.PROTOCOL_BROKEN,
        ) from err
    except OSError as err:
        raise CommunicationError(redact(str(err))) from err  # WR-05


def build_or_resume_client(  # noqa: PLR0913 — signature locked by plan 03-02 (url + auth quad + session + device_name)
    url: str,
    account_type: AccountType,
    username: str,
    password: str,
    session: dict[str, Any] | None,
    device_name: str,
) -> pronotepy.Client | pronotepy.ParentClient:
    """Resume from stored session if present, else fresh login (D-07, AUTH-04, AUTH-07).

    Args:
        url: Same as ``build_client``.
        account_type: Same as ``build_client``.
        username: Same as ``build_client``.
        password: Same as ``build_client``.
        session: dict from a prior ``client.export_credentials()`` call, or ``None``
            to skip the token_login fast path. Treated as opaque pronotepy state.
        device_name: AUTH-07 label (e.g. ``"home-assistant-abc12345"``) — surfaces
            in the user's Pronote app under "connected devices" (D-18). Passed
            via ``device_name`` kwarg to both ``token_login`` and the fresh
            constructor so the label is consistent across login modes.

    Returns:
        Same as ``build_client``.

    Raises:
        AuthError: pronotepy ``CryptoError`` during fresh login.
        RateLimitedError: pronotepy returned the literal "Your IP address is
            suspended" during fresh login.
        CommunicationError: any other pronotepy or network failure during
            fresh login. Failures of the token_login fast path are silently
            absorbed and trigger fresh login.
    """
    cls: type[pronotepy.Client | pronotepy.ParentClient]
    cls = pronotepy.ParentClient if account_type == "parent" else pronotepy.Client

    # D-07 fast path: token_login if we have stored session.
    if session is not None:
        try:
            return cls.token_login(
                url,
                username=username,
                device_name=device_name,
                **session,
            )
        except pronotepy.exceptions.CryptoError:
            pass  # stale session — fall through to fresh login.
        except pronotepy.PronoteAPIError as err:
            # WR-03: if the server already says "IP suspended" during token_login,
            # do NOT retry with a fresh-login HTTP request to the same banned IP —
            # that extends the suspension window (CLAUDE.md "politesse polling").
            # Surface the rate-limit signal so the coordinator's UpdateFailed path
            # (and Phase 5's circuit-breaker) can back off instead of hammering
            # the school server.
            if _IP_SUSPENDED_LITERAL in str(err):
                raise RateLimitedError(redact(str(err))) from err
            # Other API errors — fresh login may still work.
        except OSError:
            pass  # transient network — fresh login may still succeed.

    # Fresh login — same error mapping as ``build_client``, with device_name kwarg.
    try:
        return cls(
            url,
            username=username,
            password=password,
            device_name=device_name,
        )
    except pronotepy.exceptions.CryptoError as err:
        raise AuthError(redact(str(err))) from err  # WR-05
    except pronotepy.PronoteAPIError as err:
        msg = redact(str(err))  # WR-05
        if _IP_SUSPENDED_LITERAL in str(err):
            raise RateLimitedError(msg) from err
        raise CommunicationError(
            msg,
            reason=ErrorReason.PROTOCOL_BROKEN,
        ) from err
    except OSError as err:
        raise CommunicationError(redact(str(err))) from err  # WR-05


def set_active_child(client: pronotepy.ParentClient, child_index: int | str) -> None:
    """Apply a parent's child selection with our typed-error mapping (CR-04).

    Wraps ``client.set_child(child_index)`` so callers don't have to know
    about the underlying pronotepy exception classes. Mirrors the error
    mapping used by ``build_client`` / ``build_or_resume_client``:

    - ``pronotepy.exceptions.CryptoError`` -> ``AuthError`` (session expired
      between login and child selection — D-09's silent-recovery loop will
      catch this and trigger a fresh re-login).
    - ``pronotepy.PronoteAPIError`` containing the IP-suspended literal ->
      ``RateLimitedError`` (D-22 — Phase 5's circuit-breaker reads ``.reason``).
    - any other ``pronotepy.PronoteAPIError`` -> ``CommunicationError``
      (with ``ErrorReason.PROTOCOL_BROKEN``).
    - ``OSError`` -> ``CommunicationError`` (transient network).

    All raw exception messages are passed through ``redact()`` (WR-05).

    Args:
        client: Live ``pronotepy.ParentClient`` (the only client class with
            ``set_child``).
        child_index: 0-based index into ``client.children`` OR a string
            identifier accepted by pronotepy's ``set_child`` overload
            (D-21 — fetcher.fetch_all may pass either form).

    Raises:
        AuthError: see above.
        RateLimitedError: see above.
        CommunicationError: see above.
    """
    try:
        client.set_child(child_index)
    except pronotepy.exceptions.CryptoError as err:
        raise AuthError(redact(str(err))) from err
    except pronotepy.PronoteAPIError as err:
        msg = redact(str(err))
        if _IP_SUSPENDED_LITERAL in str(err):
            raise RateLimitedError(msg) from err
        raise CommunicationError(msg, reason=ErrorReason.PROTOCOL_BROKEN) from err
    except OSError as err:
        raise CommunicationError(redact(str(err))) from err
