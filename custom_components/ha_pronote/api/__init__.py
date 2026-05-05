"""API subpackage — pure-sync facade over pronotepy==2.14.6.

Phase 2 D-19: zero ``homeassistant.*`` imports anywhere in this package.
Phase 2 D-20: imports limited to stdlib + pronotepy + python-slugify (lazy).

Public surface (consumed by Phase 3 coordinator via ``async_add_executor_job``):

- ``build_client(url, account_type, username, password)`` — ``api/client.py`` (Task 2)
- ``fetch_all(client, today, school_tz, child_index_or_identifier=None)`` — ``api/fetcher.py`` (Task 2)
- ``AuthError``, ``CommunicationError``, ``RateLimitedError``, ``ParseError``, ``ErrorReason``

Token persistence (``client.export_credentials()``) is Phase 3's coordinator
responsibility — NOT exposed here. The coordinator owns ``entry.data`` storage
for the token round-trip (AUTH-04, PC-02-04). Adding an
``export_credentials_dict()`` wrapper to ``api/`` would couple the pure-Python
layer to HA's storage concerns; resist the temptation.

Note: Task 1 of Plan 02-01 ships ``errors``, ``models``, ``_strip``. Task 2
adds ``client.py`` and ``fetcher.py`` and replaces this re-export block with
the full surface.
"""

from .errors import AuthError, CommunicationError, ErrorReason, ParseError, PronoteIntegrationError, RateLimitedError
from .models import Grade, Information, Lesson, Snapshot

__all__ = [
    "AuthError",
    "CommunicationError",
    "ErrorReason",
    "Grade",
    "Information",
    "Lesson",
    "ParseError",
    "PronoteIntegrationError",
    "RateLimitedError",
    "Snapshot",
]
