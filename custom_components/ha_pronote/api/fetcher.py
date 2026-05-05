"""Snapshot fetch + tz-localization. Sync — caller wraps in executor.

D-15: J-7 -> J+14 fetch window (CAL-01 cross-cutting tracker for Phase 4 calendar).
D-17: ``today`` injected, NOT computed via the system clock (pure-deterministic).
D-18: ``school_tz`` injected, NO global default in ``api/``.
D-23: pronotepy returns naive datetimes in school local time (Pitfall 4) — localize here.
D-24: strip pronotepy back-refs (Anti-Pattern 5).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pronotepy

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

from ._strip import strip_client_refs
from .errors import CommunicationError, ErrorReason
from .models import Grade, Information, Lesson, Snapshot


def fetch_all(
    client: pronotepy.Client | pronotepy.ParentClient,
    today: date,
    school_tz: ZoneInfo,
    child_index_or_identifier: int | str | None = None,
) -> Snapshot:
    """Fetch lessons, grades, informations across the J-7 → J+14 window.

    Args:
        client: Authenticated pronotepy client (built via ``build_client``).
        today: Reference date for the window (D-17 — pure-deterministic).
        school_tz: Timezone of the Pronote server (D-18 — typically
            ``Pacific/Noumea`` for ``ac-noumea.nc``, ``Europe/Paris`` elsewhere).
        child_index_or_identifier: For ``ParentClient`` only (D-21). When set,
            ``ParentClient.set_child(...)`` is invoked BEFORE any fetch so
            subsequent reads return the selected child's data. When ``None``
            and ``client`` is a ParentClient, pronotepy defaults to the first
            child (no selection call). Ignored for eleve ``Client``.

    Returns:
        Plain-dataclass ``Snapshot``. NO pronotepy objects leak (D-24).

    Raises:
        CommunicationError: any failure during pronotepy fetch.
    """
    # D-21 — child selection for ParentClient lives in api/fetcher.py, not in
    # api/client.py (build_client). Phase 3's coordinator decides which child
    # to fetch and passes the index/identifier on each call.
    if isinstance(client, pronotepy.ParentClient) and child_index_or_identifier is not None:
        client.set_child(child_index_or_identifier)

    start = today - timedelta(days=7)
    end = today + timedelta(days=14)

    try:
        raw_lessons = list(client.lessons(date_from=start, date_to=end))
        raw_grades = list(client.current_period.grades) if client.current_period else []
        raw_info = list(client.information_and_surveys)
    except pronotepy.PronoteAPIError as err:
        raise CommunicationError(
            str(err),
            reason=ErrorReason.PROTOCOL_BROKEN,
        ) from err
    except OSError as err:
        raise CommunicationError(str(err)) from err

    # Strip back-refs defense-in-depth (D-24, C-05) BEFORE field-by-field copy.
    for obj in (*raw_lessons, *raw_grades, *raw_info):
        strip_client_refs(obj)

    return Snapshot(
        today=today,
        school_tz=str(school_tz),
        lessons=[_lesson_from_raw(item, school_tz) for item in raw_lessons],
        grades=[_grade_from_raw(item) for item in raw_grades],
        information=[_info_from_raw(item, school_tz) for item in raw_info],
    )


def _localize(naive_dt: datetime | None, school_tz: ZoneInfo) -> datetime | None:
    """Pronotepy returns naive datetimes in school local time (Pitfall 4)."""
    if naive_dt is None:
        return None
    if naive_dt.tzinfo is not None:
        # Defensive: pronotepy 2.14.6 returns naive, but a future version might.
        return naive_dt
    return naive_dt.replace(tzinfo=school_tz)


def _lesson_from_raw(raw: Any, school_tz: ZoneInfo) -> Lesson:
    """Field-by-field copy. NO pronotepy back-pointer (Anti-Pattern 5)."""
    start = _localize(raw.start, school_tz)
    end = _localize(raw.end, school_tz)
    if start is None or end is None:
        raise CommunicationError(
            "Lesson missing start/end datetime",
            reason=ErrorReason.PARSE_ERROR,
        )
    return Lesson(
        date=start.date(),
        start=start,
        end=end,
        subject=raw.subject.name if raw.subject else "",
        teacher=raw.teacher_name or "",
        classroom=raw.classroom or "",
        canceled=bool(raw.canceled),
        status=raw.status or "",
    )


def _grade_from_raw(raw: Any) -> Grade:
    """Field-by-field copy of a pronotepy grade."""
    return Grade(
        subject=raw.subject.name if raw.subject else "",
        value=str(raw.grade) if raw.grade is not None else "",
        out_of=str(raw.out_of) if raw.out_of is not None else "",
        coefficient=str(raw.coefficient) if raw.coefficient is not None else "",
        date=raw.date,
    )


def _info_from_raw(raw: Any, school_tz: ZoneInfo) -> Information:
    """Field-by-field copy of a pronotepy information / survey."""
    published = _localize(raw.start_date, school_tz) or _localize(
        getattr(raw, "creation_date", None),
        school_tz,
    )
    if published is None:
        raise CommunicationError(
            "Information missing date",
            reason=ErrorReason.PARSE_ERROR,
        )
    return Information(
        info_id=str(raw.id),
        title=raw.title or "",
        sender=getattr(raw, "author", "") or "",
        date=published,
        excerpt=(raw.content or "")[:500],
        read=bool(getattr(raw, "read", False)),
    )
