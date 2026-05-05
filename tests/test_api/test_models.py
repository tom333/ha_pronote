"""Round-trip and slicing contract tests for api/models.py (D-11, D-16, D-23)."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timedelta
import json
from zoneinfo import ZoneInfo

import pytest

from custom_components.ha_pronote.api import Grade, Information, Lesson, ParseError, Snapshot

NOUMEA = ZoneInfo("Pacific/Noumea")


def _make_lesson(d: date, hour: int = 8, subject: str = "Maths") -> Lesson:
    start = datetime(d.year, d.month, d.day, hour, 0, tzinfo=NOUMEA)
    end = datetime(d.year, d.month, d.day, hour + 1, 0, tzinfo=NOUMEA)
    return Lesson(
        date=d,
        start=start,
        end=end,
        subject=subject,
        teacher="M. X",
        classroom="A1",
        canceled=False,
        status="",
    )


def test_lesson_to_from_dict_roundtrip():
    L = _make_lesson(date(2026, 5, 4))
    d = L.to_dict()
    assert Lesson.from_dict(d) == L


def test_grade_to_from_dict_roundtrip():
    G = Grade(
        subject="Maths",
        value="14,5",
        out_of="20",
        coefficient="1",
        date=date(2026, 5, 4),
    )
    assert Grade.from_dict(G.to_dict()) == G


def test_information_to_from_dict_roundtrip():
    info = Information(
        info_id="abc",
        title="Réunion",
        sender="M. Directeur",
        date=datetime(2026, 5, 4, 9, 0, tzinfo=NOUMEA),
        excerpt="Réunion parents-profs",
        read=False,
    )
    assert Information.from_dict(info.to_dict()) == info


def test_snapshot_to_from_dict_roundtrip():
    today = date(2026, 5, 4)
    snap = Snapshot(
        today=today,
        school_tz="Pacific/Noumea",
        lessons=[_make_lesson(today)],
        grades=[
            Grade(
                subject="Maths",
                value="14,5",
                out_of="20",
                coefficient="1",
                date=today,
            )
        ],
        information=[
            Information(
                info_id="i1",
                title="t",
                sender="s",
                date=datetime(today.year, today.month, today.day, 8, 0, tzinfo=NOUMEA),
                excerpt="e",
                read=False,
            )
        ],
    )
    assert Snapshot.from_dict(snap.to_dict()) == snap


def test_snapshot_lessons_today_filters_to_today():
    today = date(2026, 5, 4)
    snap = Snapshot(
        today=today,
        school_tz="Pacific/Noumea",
        lessons=[
            _make_lesson(today - timedelta(days=1)),
            _make_lesson(today),
            _make_lesson(today + timedelta(days=1)),
        ],
        grades=[],
        information=[],
    )
    todays = snap.lessons_today
    assert len(todays) == 1
    assert todays[0].date == today


def test_snapshot_lessons_tomorrow_filters_to_tomorrow():
    today = date(2026, 5, 4)
    snap = Snapshot(
        today=today,
        school_tz="Pacific/Noumea",
        lessons=[
            _make_lesson(today - timedelta(days=1)),
            _make_lesson(today),
            _make_lesson(today + timedelta(days=1)),
        ],
        grades=[],
        information=[],
    )
    tomorrows = snap.lessons_tomorrow
    assert len(tomorrows) == 1
    assert tomorrows[0].date == today + timedelta(days=1)


def test_lesson_dataclass_is_frozen():
    L = _make_lesson(date(2026, 5, 4))
    with pytest.raises(dataclasses.FrozenInstanceError):
        L.subject = "X"  # type: ignore[misc]


def test_snapshot_dataclass_is_frozen():
    snap = Snapshot(
        today=date(2026, 5, 4),
        school_tz="Pacific/Noumea",
        lessons=[],
        grades=[],
        information=[],
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.school_tz = "Europe/Paris"  # type: ignore[misc]


def test_from_dict_rejects_naive_datetime_lesson():
    with pytest.raises(ParseError):
        Lesson.from_dict(
            {
                "date": "2026-05-04",
                "start": "2026-05-04T08:00:00",
                "end": "2026-05-04T09:00:00",
                "subject": "Maths",
                "teacher": "M. X",
                "classroom": "A1",
                "canceled": False,
                "status": "",
            }
        )


def test_from_dict_rejects_naive_datetime_information():
    with pytest.raises(ParseError):
        Information.from_dict(
            {
                "info_id": "x",
                "title": "t",
                "sender": "s",
                "date": "2026-05-04T09:00:00",
                "excerpt": "e",
                "read": False,
            }
        )


def test_lesson_to_dict_is_json_serializable():
    L = _make_lesson(date(2026, 5, 4))
    json.dumps(L.to_dict())  # must not raise
