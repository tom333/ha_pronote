"""Local fixtures for tests/test_diff/. NO PHACC autouse — diff/ is HA-free per D-19.

The root ``tests/conftest.py`` defines an autouse fixture that requires PHACC's
``enable_custom_integrations`` — that fixture only loads when the HA test
harness is available. ``tests/test_diff/`` is pure-Python (D-19), so we OVERRIDE
the autouse here with a no-op of the same name. The override means the
diff/ test suite runs without the HA harness installed (matches D-19 boundary).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override the root autouse — diff/ is HA-free per D-19."""
    return
