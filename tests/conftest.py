"""Shared fixtures for HA-Pronote tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests.

    Without this, the ``hass`` fixture refuses to load anything from
    ``custom_components/`` and our integration would be invisible.
    """
    yield
