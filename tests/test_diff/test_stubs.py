"""Tests for the Phase 2 type-locked stubs (D-02). Bodies land in Phase 4."""

from __future__ import annotations

import pytest

from custom_components.ha_pronote.diff import diff_grades, diff_notifications


def test_diff_grades_raises_not_implemented():
    with pytest.raises(NotImplementedError, match=r"Phase 4|D-02"):
        diff_grades(None, None)  # type: ignore[arg-type]


def test_diff_notifications_raises_not_implemented():
    with pytest.raises(NotImplementedError, match=r"Phase 4|D-02"):
        diff_notifications(None, None)  # type: ignore[arg-type]
