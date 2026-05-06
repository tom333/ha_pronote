"""Diff lessons -- identity vs content key, room vs cancellation discrimination.

Algorithm derivation: tests/fixtures/SPIKE-FINDINGS-bain3-311.md (D-06, D-07).
Read that document FIRST -- its identity-vs-content split is the contract this
module implements.

Frozen taxonomy (D-09, ROADMAP Phase 4 success criterion #1):

- ``"canceled"`` -- ``canceled`` flag flipped from ``False`` to ``True`` between polls
- ``"modified"`` -- content changed but identity matched (catch-all)
- ``"teacher"`` -- teacher field changed (subset of "modified")
- ``"room"``    -- classroom field changed (subset of "modified")

First-poll invariant (D-08, EVENT-04 cross-cutting tracker for Phase 4):
``diff_lessons(None, snapshot, day) -> []`` regardless of snapshot size.

Reorder no-op invariant (Pitfall 10):
Same identity + content tuples regardless of array order -> ``[]``.

Plan 02-03 Task 1 ships only the placeholder so ``diff/__init__.py`` re-exports
work. Task 3 implements the algorithm against synthetic + real fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.ha_pronote.api.models import Snapshot

    from .events import DayLabel, LessonChange


def diff_lessons(
    previous: Snapshot | None,
    new: Snapshot,
    day: DayLabel,
) -> list[LessonChange]:
    """Return ``LessonChange`` events between two snapshots for the requested day.

    Phase 2 Task 1 placeholder -- Task 3 implements the full identity-vs-content
    algorithm. The first-poll invariant (D-08) is honoured here so downstream
    consumers can already rely on the empty-list-on-first-poll contract.

    Args:
        previous: Previous ``Snapshot``, or ``None`` on first poll after restart.
        new: Current ``Snapshot``.
        day: ``"today"`` or ``"tomorrow"`` -- selects the lesson slice to compare.

    Returns:
        List of ``LessonChange`` events. Empty when ``previous`` is ``None``
        (D-08 invariant). Task 3 fills in the non-empty branch against
        synthetic + real fixtures.
    """
    if previous is None:
        return []
    # Task 3 implements the diff body. Until then, conservatively emit nothing.
    return []
