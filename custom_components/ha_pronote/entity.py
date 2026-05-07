"""Base entity class for HA-Pronote (C-01, D-15, D-17, ENT-03).

C-01: single source of truth for the CoordinatorEntity base. Phase 4's
calendar.py and grades/notifications sensors will subclass this same base
without circular-dep risk (sensor.py would otherwise be the import target).

D-15: ``_attr_has_entity_name = True`` + ``_attr_translation_key`` (declared
on each concrete subclass) is HA's modern naming convention. The display
name comes from strings.json ``entity.sensor.{translation_key}.name``.

D-17 — DeviceInfo:
  identifiers = {(DOMAIN, child_identifier)}
  name        = entry.data["child_name"]
  manufacturer = "Pronote"
NO ``model`` field — ROADMAP Phase 4 success criterion #2 explicitly says
the class-level model attribute lands in Phase 4. NO ``sw_version``, NO
``configuration_url`` in Phase 3.

available: delegates to ``self.coordinator.last_update_success`` so a poll
failure flips every entity to ``unavailable`` until the next successful
refresh.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

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
        """D-17 — DeviceInfo from runtime_data + entry.data['child_name']."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.runtime_data.child_identifier)},
            name=self._entry.data["child_name"],
            manufacturer="Pronote",
        )

    @property
    def available(self) -> bool:
        """D-15 — coordinator failure -> entity unavailable."""
        return self.coordinator.last_update_success
