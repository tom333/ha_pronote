---
status: partial
phase: 03-coordinator-first-sensor
source: [03-VERIFICATION.md]
started: 2026-05-07T03:00:00Z
updated: 2026-05-07T05:00:00Z
---

## Current Test

[awaiting human testing — code-review --auto fix loop completed clean (0 BLOCKER, 0 WARNING, 3 INFO carried forward)]

## Tests

### 1. Live HA install end-to-end — config flow add + password-masking spot-check (CR-01 fix sign-off)
expected: Wrong password produces `invalid_auth` error in form (no entry persisted). On valid creds, entry appears with title `<child_name> (<account_type>)`. **Visual: password field MUST be masked** — CR-01 fix applies `TextSelector(TextSelectorConfig(type=PASSWORD))`; this UAT confirms HA renders the mask correctly.
result: [pending]

### 2. HA restart — entry resumes without re-auth + Pronote app device visibility (SC#2)
expected: After restart, no UI prompt; `sensor.pronote_<child>_lessons_today` resumes its numeric state on the next poll. In the Pronote app, a connected device named `home-assistant-<8 hex>` is visible (manually revocable).
result: [pending]

### 3. HA log inspection — zero "Detected blocking call" warnings during a poll (SC#3)
expected: No `Detected blocking call` lines emitted by HA's runtime detector during `async_setup_entry` first_refresh nor on the next polling cycle. WR-08 fix made the automated test substantive (real `time.sleep` via mock client) — this UAT is now a confirmation step rather than the only line of defense.
result: [pending]

### 4. CI run — full HA-side test suite under Python 3.14.2 / HA 2026.4.x
expected: All ~95 HA-importing tests pass: `pytest tests/test_init.py tests/test_config_flow.py tests/test_coordinator.py tests/test_sensor.py tests/test_token_persistence.py tests/test_api/test_client.py tests/test_api/test_errors.py tests/test_api/test_fetcher.py`. Local env (Python 3.13.9) cannot run these — conftest imports `MockConfigEntry` which needs PHACC + HA 3.14.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
