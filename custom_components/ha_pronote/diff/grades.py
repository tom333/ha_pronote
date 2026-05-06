"""Grade diff -- body lands in Phase 4 (D-02). Type contract locked here.

Phase 2 ships ``NewGrade`` (in ``diff/events.py`` per C-01). Phase 4 fills this
body. The function signature below freezes Phase 4's contract so it cannot
drift across phases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.ha_pronote.api.models import Snapshot

    from .events import NewGrade


def diff_grades(previous: Snapshot | None, new: Snapshot) -> list[NewGrade]:
    """Return new grades since the previous poll.

    Phase 2 stub. Phase 4 fills the body per D-02:

    - first-poll skip: ``previous is None -> []``.
    - identity key per grade: ``(subject, date, value)`` -- set difference.

    Raises:
        NotImplementedError: until Phase 4 ships.
    """
    raise NotImplementedError(
        "diff_grades body lands in Phase 4 (D-02). Phase 2 ships only the NewGrade dataclass contract."
    )
