"""Contract tests for api/fetcher.py (D-15, D-17, D-18, D-21, D-23, D-24)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pronotepy
import pytest

from custom_components.ha_pronote.api import CommunicationError, ErrorReason, Snapshot, fetch_all

NOUMEA = ZoneInfo("Pacific/Noumea")
PARIS = ZoneInfo("Europe/Paris")


def _fake_subject(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


class _FakeLesson:
    def __init__(  # noqa: PLR0913 — test fake mirrors pronotepy's wide Lesson surface
        self,
        start: datetime,
        end: datetime,
        subject: str = "Maths",
        teacher_name: str = "M. X",
        classroom: str = "A1",
        canceled: bool = False,
        status: str = "",
    ) -> None:
        self.start = start
        self.end = end
        self.subject = _fake_subject(subject)
        self.teacher_name = teacher_name
        self.classroom = classroom
        self.canceled = canceled
        self.status = status


class _FakeGrade:
    def __init__(
        self,
        subject: str = "Maths",
        grade: str = "14,5",
        out_of: str = "20",
        coefficient: str = "1",
        graded_on: date | None = None,
    ) -> None:
        self.subject = _fake_subject(subject)
        self.grade = grade
        self.out_of = out_of
        self.coefficient = coefficient
        self.date = graded_on or date(2026, 5, 4)


class _FakeInfo:
    def __init__(  # noqa: PLR0913 — test fake mirrors pronotepy's Information surface
        self,
        info_id: str = "i1",
        title: str = "t",
        author: str = "M. Directeur",
        start_date: datetime | None = None,
        content: str = "Réunion",
        read: bool = False,
    ) -> None:
        self.id = info_id
        self.title = title
        self.author = author
        self.start_date = start_date
        self.content = content
        self.read = read


class _FakePeriod:
    def __init__(self, grades: list) -> None:
        self.grades = grades


class _FakeClient:
    """Minimal fake replacement for pronotepy.Client.

    Tracks the (date_from, date_to) call to ``lessons`` so D-15 can be asserted.
    """

    def __init__(
        self,
        lessons: list | None = None,
        grades: list | None = None,
        info: list | None = None,
    ) -> None:
        self._lessons = lessons or []
        self.current_period = _FakePeriod(grades) if grades is not None else None
        self.information_and_surveys = info or []
        self.last_call: tuple | None = None

    def lessons(self, date_from: date, date_to: date) -> list:
        self.last_call = (date_from, date_to)
        return self._lessons


def test_fetch_all_window_is_today_minus_7_to_today_plus_14():
    client = _FakeClient()
    today = date(2026, 5, 4)
    fetch_all(client, today=today, school_tz=NOUMEA)
    assert client.last_call == (date(2026, 4, 27), date(2026, 5, 18))


def test_fetch_all_uses_injected_today_not_datetime_now():
    client = _FakeClient()
    today = date(2020, 1, 1)
    fetch_all(client, today=today, school_tz=NOUMEA)
    # Window is today-7 .. today+14 == 2019-12-25 .. 2020-01-15
    assert client.last_call == (date(2019, 12, 25), date(2020, 1, 15))


def test_naive_pronotepy_datetimes_are_localized_to_school_tz():
    naive_start = datetime(2026, 5, 4, 8, 0)
    naive_end = datetime(2026, 5, 4, 9, 0)
    client = _FakeClient(lessons=[_FakeLesson(naive_start, naive_end)])
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    assert len(snap.lessons) == 1
    L = snap.lessons[0]
    assert L.start.tzinfo is not None
    assert L.end.tzinfo is not None
    # Pacific/Noumea is +11:00 always (no DST)
    assert L.start.utcoffset() == timedelta(hours=11)


def test_paris_summer_offset_is_plus_2():
    naive_start = datetime(2026, 7, 15, 8, 0)
    naive_end = datetime(2026, 7, 15, 9, 0)
    client = _FakeClient(lessons=[_FakeLesson(naive_start, naive_end)])
    snap = fetch_all(client, today=date(2026, 7, 15), school_tz=PARIS)
    L = snap.lessons[0]
    assert L.start.utcoffset() == timedelta(hours=2)


def test_no_pronotepy_objects_leak_into_snapshot():
    naive_start = datetime(2026, 5, 4, 8, 0)
    naive_end = datetime(2026, 5, 4, 9, 0)
    client = _FakeClient(lessons=[_FakeLesson(naive_start, naive_end)])
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    for L in snap.lessons:
        assert L.__class__.__module__.startswith("custom_components.ha_pronote.api")


def test_no_back_refs_on_returned_lessons():
    naive_start = datetime(2026, 5, 4, 8, 0)
    naive_end = datetime(2026, 5, 4, 9, 0)
    client = _FakeClient(lessons=[_FakeLesson(naive_start, naive_end)])
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    for L in snap.lessons:
        assert getattr(L, "client", None) is None
        assert getattr(L, "_session", None) is None


def test_school_tz_is_stored_as_string():
    client = _FakeClient()
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    assert snap.school_tz == str(NOUMEA)


def test_pronote_api_error_during_lessons_raises_communication_error():
    class _ErrClient:
        current_period: ClassVar = _FakePeriod([])
        information_and_surveys: ClassVar[list] = []

        def lessons(self, date_from: date, date_to: date) -> list:
            raise pronotepy.PronoteAPIError("Some failure")

    with pytest.raises(CommunicationError) as excinfo:
        fetch_all(_ErrClient(), today=date(2026, 5, 4), school_tz=NOUMEA)
    assert excinfo.value.reason == ErrorReason.PROTOCOL_BROKEN


def test_os_error_during_lessons_raises_communication_error_server_down():
    class _ErrClient:
        current_period: ClassVar = _FakePeriod([])
        information_and_surveys: ClassVar[list] = []

        def lessons(self, date_from: date, date_to: date) -> list:
            raise OSError("net down")

    with pytest.raises(CommunicationError) as excinfo:
        fetch_all(_ErrClient(), today=date(2026, 5, 4), school_tz=NOUMEA)
    assert excinfo.value.reason == ErrorReason.SERVER_DOWN


def test_grades_are_copied_into_plain_dataclasses():
    client = _FakeClient(grades=[_FakeGrade()])
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    assert len(snap.grades) == 1
    assert snap.grades[0].subject == "Maths"
    assert snap.grades[0].value == "14,5"


def test_information_uses_localized_start_date():
    naive = datetime(2026, 5, 4, 9, 0)
    client = _FakeClient(info=[_FakeInfo(start_date=naive)])
    snap = fetch_all(client, today=date(2026, 5, 4), school_tz=NOUMEA)
    assert len(snap.information) == 1
    assert snap.information[0].date.utcoffset() == timedelta(hours=11)


def test_fetch_all_returns_snapshot_with_today_field():
    client = _FakeClient()
    today = date(2026, 5, 4)
    snap = fetch_all(client, today=today, school_tz=NOUMEA)
    assert isinstance(snap, Snapshot)
    assert snap.today == today


def test_fetch_all_calls_set_child_for_parent_client_with_index():
    mock = MagicMock(spec=pronotepy.ParentClient)
    mock.lessons.return_value = []
    mock.current_period = _FakePeriod([])
    mock.information_and_surveys = []
    fetch_all(
        mock,
        today=date(2026, 5, 4),
        school_tz=NOUMEA,
        child_index_or_identifier=0,
    )
    mock.set_child.assert_called_once_with(0)


def test_fetch_all_calls_set_child_for_parent_client_with_string_identifier():
    mock = MagicMock(spec=pronotepy.ParentClient)
    mock.lessons.return_value = []
    mock.current_period = _FakePeriod([])
    mock.information_and_surveys = []
    fetch_all(
        mock,
        today=date(2026, 5, 4),
        school_tz=NOUMEA,
        child_index_or_identifier="abc",
    )
    mock.set_child.assert_called_once_with("abc")


def test_fetch_all_skips_set_child_for_eleve_client():
    mock = MagicMock(spec=pronotepy.Client)
    mock.lessons.return_value = []
    mock.current_period = _FakePeriod([])
    mock.information_and_surveys = []
    fetch_all(
        mock,
        today=date(2026, 5, 4),
        school_tz=NOUMEA,
        child_index_or_identifier=0,
    )
    # spec=pronotepy.Client forbids accessing set_child (not an attribute of
    # the eleve Client). The fact that fetch_all completes is itself the proof
    # the call site is gated. Accessing it now would raise AttributeError.
    with pytest.raises(AttributeError):
        mock.set_child  # noqa: B018


def test_fetch_all_skips_set_child_for_parent_client_when_identifier_none():
    mock = MagicMock(spec=pronotepy.ParentClient)
    mock.lessons.return_value = []
    mock.current_period = _FakePeriod([])
    mock.information_and_surveys = []
    fetch_all(
        mock,
        today=date(2026, 5, 4),
        school_tz=NOUMEA,
        child_index_or_identifier=None,
    )
    assert mock.set_child.call_count == 0


# --- 02-02 spike findings: defensive fallback when Pronote omits grades ---

class _GradesKeyErrorPeriod:
    """current_period exists but `.grades` raises KeyError.

    Reproduces the pronotepy 2.14.6 path observed during the 02-02 spike on a
    parent account: ``response["dataSec"]["data"]["listeDevoirs"]["V"]`` fires
    ``KeyError('listeDevoirs')`` when Pronote did not include the listing.
    """

    @property
    def grades(self) -> list:
        raise KeyError("listeDevoirs")


class _GradesAttributeErrorPeriod:
    """Defensive: pronotepy could also surface AttributeError mid-traversal."""

    @property
    def grades(self) -> list:
        raise AttributeError("grades")


def test_keyerror_on_current_period_grades_returns_empty_grades(
):
    """02-02 spike finding: pronotepy raises KeyError('listeDevoirs') when the
    Pronote response omits the grades section. fetch_all must downgrade to
    grades=[] rather than fail the whole snapshot — lessons + information are
    the Core Value path."""
    naive_start = datetime(2026, 5, 4, 8, 0)
    naive_end = datetime(2026, 5, 4, 9, 0)

    class _Client:
        information_and_surveys: ClassVar[list] = []

        def __init__(self) -> None:
            self.current_period = _GradesKeyErrorPeriod()

        def lessons(self, date_from: date, date_to: date) -> list:
            return [_FakeLesson(naive_start, naive_end)]

    snap = fetch_all(_Client(), today=date(2026, 5, 4), school_tz=NOUMEA)
    assert snap.grades == []
    assert len(snap.lessons) == 1


def test_attributeerror_on_current_period_grades_returns_empty_grades():
    """Defensive twin of the KeyError test — pronotepy may raise AttributeError
    on a similar schema gap. Same downgrade applies."""

    class _Client:
        information_and_surveys: ClassVar[list] = []

        def __init__(self) -> None:
            self.current_period = _GradesAttributeErrorPeriod()

        def lessons(self, date_from: date, date_to: date) -> list:
            return []

    snap = fetch_all(_Client(), today=date(2026, 5, 4), school_tz=NOUMEA)
    assert snap.grades == []
