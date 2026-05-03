"""HA-Pronote — Home Assistant integration for Pronote.

Phase 1: package skeleton only. The coordinator, sensors, calendar entity, and
real Config Flow ship in subsequent phases (see ROADMAP.md). This file is
intentionally minimal so the integration can be loaded by HA / HACS without
exposing any runtime behavior yet.
"""

from .const import DOMAIN

__all__ = ["DOMAIN"]
