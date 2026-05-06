"""Information diff -- body lands in Phase 4 (D-02). Type contract locked here.

Phase 2 ships ``NewInformation`` (in ``diff/events.py`` per C-01). Phase 4 fills
this body. The function signature below freezes Phase 4's contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.ha_pronote.api.models import Snapshot

    from .events import NewInformation


def diff_notifications(
    previous: Snapshot | None,
    new: Snapshot,
) -> list[NewInformation]:
    """Return new informations since the previous poll.

    Phase 2 stub. Phase 4 fills the body per D-02:

    - first-poll skip: ``previous is None -> []``.
    - identity key per information: ``(info_id, date)`` -- set difference.

    Raises:
        NotImplementedError: until Phase 4 ships.
    """
    raise NotImplementedError(
        "diff_notifications body lands in Phase 4 (D-02). Phase 2 ships only the NewInformation dataclass contract."
    )
