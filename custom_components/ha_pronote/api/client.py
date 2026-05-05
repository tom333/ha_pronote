"""Sync facade over pronotepy. HA-free per D-19/D-20.

Caller (Phase 3 coordinator) wraps in ``await hass.async_add_executor_job(partial(...))``.
"""

from __future__ import annotations

from typing import Literal

import pronotepy

from .errors import AuthError, CommunicationError, ErrorReason, RateLimitedError

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
        raise AuthError(str(err)) from err
    except pronotepy.PronoteAPIError as err:
        if _IP_SUSPENDED_LITERAL in str(err):
            raise RateLimitedError(str(err)) from err
        raise CommunicationError(
            str(err),
            reason=ErrorReason.PROTOCOL_BROKEN,
        ) from err
    except OSError as err:
        raise CommunicationError(str(err)) from err
