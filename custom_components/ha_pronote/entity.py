"""Base entity class for HA-Pronote (C-01, D-15, D-17, D-19, ENT-01, ENT-03).

C-01: single source of truth for the CoordinatorEntity base. Phase 4's
calendar.py and grades/notifications sensors will subclass this same base
without circular-dep risk (sensor.py would otherwise be the import target).

D-15: ``_attr_has_entity_name = True`` + ``_attr_translation_key`` (declared
on each concrete subclass) is HA's modern naming convention. The display
name comes from strings.json ``entity.sensor.{translation_key}.name``.

D-17 / D-19 — DeviceInfo:
  identifiers = {(DOMAIN, child_identifier)}
  name        = entry.data["child_name"]
  manufacturer = "Pronote"
  model       = class level (D-19, ENT-01) — sourced from ClientInfo.class_name
                for eleve accounts, or children[child_index].class_name for
                ParentClient accounts (PHASE-4-PROBE-NOTES.md STEP 11).
                Empty string maps to None (HA hides the row).
NO ``sw_version``, NO ``configuration_url`` in Phase 3.

available: WR-01 — we DO NOT override CoordinatorEntity.available. The base
class already returns ``super().available and self.coordinator.last_update_success``;
overriding it here with just ``self.coordinator.last_update_success`` would
silently drop the ``super().available`` term, breaking any future subclass
that sets ``_attr_available = False`` for a missing data slice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pronotepy
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CLASS_LEVEL_ATTR, DOMAIN

if TYPE_CHECKING:
    from .coordinator import PronoteDataUpdateCoordinator
    from .data import PronoteConfigEntry


class PronoteEntity(CoordinatorEntity["PronoteDataUpdateCoordinator"]):
    """Base for every HA-Pronote entity (C-01, D-15)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PronoteDataUpdateCoordinator,
        entry: PronoteConfigEntry,
    ) -> None:
        """Bind to coordinator + entry; subclass declares unique_id + translation_key."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """D-17 extended with Phase 4 D-19 — DeviceInfo.model = class level from ClientInfo.

        CLASS_LEVEL_ATTR = "class_name" — probe-confirmed in PHASE-4-PROBE-NOTES.md STEP 11.

        Parent vs eleve branching (probe finding):
        - ParentClient: client.info.class_name == "" (parent has no class).
          The child's class lives in client.children[child_index].class_name.
          set_child() does NOT swap client.info — client.info remains the parent's.
        - Client (eleve): class_name is on client.info directly.

        getattr(..., None): explicit visible default — not a catch (no silent exceptions).
        ClientInfo.class_name returns "" when absent, not None. "or None" converts "" → None.
        None hides the "Model" row in HA's device panel (D-19: acceptable per CONTEXT.md).
        """
        client = self._entry.runtime_data.client
        if isinstance(client, pronotepy.ParentClient):
            child_index = self._entry.runtime_data.child_index
            if child_index is not None:
                info_obj = client.children[child_index]
            else:
                # Fallback: parent client must have a child_index per Phase 3 D-08,
                # but if absent (corrupted entry), fall back to parent info (returns "").
                info_obj = client.info
        else:
            info_obj = client.info
        class_label = getattr(info_obj, CLASS_LEVEL_ATTR, None) or None  # "" -> None
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.runtime_data.child_identifier)},
            name=self._entry.data["child_name"],
            manufacturer="Pronote",
            model=class_label,  # D-19: None hides the row in HA device panel
        )

    # WR-01: do NOT override .available — CoordinatorEntity.available already
    # returns ``super().available and self.coordinator.last_update_success``.
    # Overriding it would drop ``super().available`` and silently mis-handle
    # any future subclass that sets ``_attr_available = False`` for a missing
    # data slice.
