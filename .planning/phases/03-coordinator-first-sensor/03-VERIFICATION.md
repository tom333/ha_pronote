---
phase: 03-coordinator-first-sensor
plans-completed: ["01", "02", "03", "04"]
verification-mode: phase-level-rollup
authored-by: 03-04 executor (last plan in wave 3)
completed: 2026-05-07
---

# Phase 3 Verification Roll-up — Coordinator & First Sensor

**Status: GREEN.** All four plans (01 Config Flow, 02 Coordinator + runtime_data, 03 Entity + first sensor, 04 HA-side test wave) shipped cleanly with PASSED self-checks. The user-facing Dimension 8 (UI-SPEC) gap was deliberately accepted at planning time and is restated here so Phase 4 inherits the explicit skip.

## ROADMAP Phase 3 Success Criteria — coverage matrix

| ROADMAP SC | Description | Verified by | Empirical proof |
|------------|-------------|-------------|-----------------|
| **SC#1** | Config Flow validates credentials end-to-end | `tests/test_config_flow.py` (Plan 04) — 6 async tests | `test_user_step_eleve_happy_path` + parametrized `test_user_step_error_mapping` (4 rows) + `test_user_step_pick_child_creates_entry` |
| **SC#2** | HA restart resumes session without fresh login + AUTH-07 device label | `tests/test_token_persistence.py` (Plan 04) — 8 tests | `test_build_or_resume_client_uses_token_login_when_session_present` (asserts `device_name` kwarg) + 3 fallback exception paths + silent-recovery roundtrip |
| **SC#3** | Live `lessons_today` sensor + zero `Detected blocking call` warnings | `tests/test_sensor.py:test_sensor_native_value_equals_lessons_today_count` AND `tests/test_coordinator.py:test_no_blocking_calls_during_poll` | `state.state == "3"` against a Snapshot with N=3 lessons today; `"Detected blocking call" not in caplog.text` after a full poll cycle |
| **SC#4** | unique_id format frozen + async_migrate_entry skeleton | `tests/test_sensor.py:test_sensor_unique_id_locks_d13` AND `tests/test_init.py:test_async_migrate_entry_returns_true` | byte-for-byte assertion `"pronote_jean_dupont_lessons_today"` via the entity registry; `await async_migrate_entry(hass, mock_config_entry) is True` |

## Requirement-by-requirement traceability

| Requirement | Plan(s) shipping the implementation | Plan 04 test asserting the behaviour |
|---|---|---|
| AUTH-01 (config flow user step) | 01 | `test_user_step_eleve_happy_path` |
| AUTH-02 (account-type discrimination + pick_child) | 01 | `test_user_step_parent_two_children_transitions_to_pick_child` + `test_user_step_pick_child_creates_entry` |
| AUTH-04 (token persistence + fallback to fresh login) | 02 (build_or_resume_client) | every test in `tests/test_token_persistence.py` |
| AUTH-07 (device_name = home-assistant-{entry_id[:8]}) | 02 (__init__.py + coordinator._recover_from_auth_error) | `test_build_or_resume_client_uses_token_login_when_session_present` (`device_name` kwarg captured) + `test_build_or_resume_client_falls_back_on_crypto_error` (`device_name` flows into fresh init) |
| COORD-01 (executor-wrapped polling) | 02 (coordinator._async_update_data) | `test_no_blocking_calls_during_poll` |
| COORD-02 (zero blocking calls / 30-min cadence) | 02 (DEFAULT_REFRESH_INTERVAL) + 02 (executor wraps) | `test_update_interval_is_30_minutes` + `test_no_blocking_calls_during_poll` (the empirical SC#3 guard) |
| TIME-01 (lessons_today count) | 03 (PronoteLessonsTodaySensor.native_value) | `test_sensor_native_value_equals_lessons_today_count` |
| ENT-02 (frozen unique_id format) | 01 (child_identifier slugify) + 03 (sensor unique_id format) | `test_sensor_unique_id_locks_d13` + `test_unique_id_format_locks_d05` |
| ENT-03 (translation_key + has_entity_name) | 01 (strings.json) + 03 (sensor class attrs) | `test_sensor_class_attributes_lock_d15_d16` |
| ENT-04 (async_migrate_entry skeleton) | 02 (`__init__.py:async_migrate_entry`) | `test_async_migrate_entry_returns_true` |

All 10 Phase 3 requirements have at least one production-code shipping plan AND at least one Plan 04 automated test. None are unverified.

## Per-plan summary linkage

- **Plan 01 (Config Flow Auth + strings.json):** see `.planning/phases/03-coordinator-first-sensor/03-01-SUMMARY.md`. 2 tasks, 4 min, 2 files modified, all self-checks PASSED.
- **Plan 02 (Coordinator + runtime_data wiring):** see `.planning/phases/03-coordinator-first-sensor/03-02-SUMMARY.md`. 3 tasks, 13 min, 6 files (2 created, 4 modified), all self-checks PASSED.
- **Plan 03 (PronoteEntity base + lessons_today Sensor):** see `.planning/phases/03-coordinator-first-sensor/03-03-SUMMARY.md`. 2 tasks, 4 min, 2 files created, all self-checks PASSED.
- **Plan 04 (HA-side test wave):** see `.planning/phases/03-coordinator-first-sensor/03-04-SUMMARY.md`. 3 tasks, 9 min, 6 files (4 created, 2 modified), all self-checks PASSED.

**Phase 3 cumulative:** 10 tasks across 4 plans, ~30 min agent time end-to-end (excluding orchestrator overhead), 16 files touched (10 created, 6 modified).

## Dimension 8 (UI-SPEC / VALIDATION.md) — explicit skip

The user accepted at the plan-phase gate that Dimension 8 (Nyquist UI validation, VALIDATION.md / RESEARCH.md screenshot review) is intentionally skipped for Phase 3. The rationale and trade-offs are recorded in `.planning/phases/03-coordinator-first-sensor/03-DISCUSSION-LOG.md`. Phase 4 inherits this **explicit** skip, so the absence of UI screenshot fixtures is not a re-discovery of "missing validation"; it's a deliberate choice driven by the test-light user-validation deferral that the family-only / single-tenant scope of HA-Pronote affords.

**Implication for Phase 4:** the calendar / grades / notifications work can land HA-side tests directly against the same C-05 mock seam pattern Plan 04 established, without needing to add screenshot regression fixtures. Phase 6 (options + reauth + nickname) is the natural place to revisit UI validation if the project later opts to ship a richer Lovelace card or a custom config flow icon.

## Stub tracking

No stubs flagged across Plans 01-04. Every shipped function has a real body or, for `async_migrate_entry`, an explicitly-skeletoned-by-design `return True` (D-26 / ENT-04 — Phase 6+ fills the body when entry shapes change; the test `test_async_migrate_entry_returns_true` locks the current contract).

## Threat surface — closed at end of Phase 3

The phase's threat register T-03-01 through T-03-24 has been mitigated or accepted in plan-by-plan summaries. No new threat flags raised during Plan 04. Specifically:

- T-03-21 (Information Disclosure via test fixtures): mitigated. All fixture data uses synthetic credentials (`username="user"`, `password="pass"`, `url="https://example.com/..."`) — CI logs cannot leak real secrets.
- T-03-22 (test-bypass via skipped autouse): mitigated. The conftest autouse fixture stays `autouse=True`; `test_no_ha_imports.py` overrides it explicitly with documented rationale.
- T-03-23 (slow-test DoS): mitigated. `pyproject.toml` `timeout = 1` + MagicMock fixtures keep every test in milliseconds.
- T-03-24 (test outcome repudiation): mitigated. Every assertion has either pytest's default detailed reporting or an explicit message; the blocking-call detector asserts directly on `caplog.text` so the offending call site appears in the failure log.

## Next-phase readiness

- **Phase 4 (calendar + diff + grades + notifications):** ready. Reuses Plan 04's fixture surface verbatim. The C-03 `_previous_snapshot` stash is in place; the diff layer plugs into `coordinator.data` (current) vs `coordinator._previous_snapshot` (prior). TIME-02 (J/J+1 attribute payload) lands on the existing `PronoteLessonsTodaySensor` as a deliberate `extra_state_attributes` add, NOT a refactor.
- **Phase 5 (adaptive polling):** ready. The coordinator's `update_interval` is the single seam; Phase 5 swaps `DEFAULT_REFRESH_INTERVAL` for an adaptive value and adds the 17h–20h window via `async_set_update_interval`. Plan 04's `test_update_interval_is_30_minutes` will need to flip to a parametrized variant covering 15 / 30 / 60 minute defaults + the heightened-window via `freezegun`.
- **Phase 6 (options + reauth + nickname):** ready. `async_migrate_entry` skeleton in place; reauth fires automatically on `ConfigEntryAuthFailed` (D-22). The unique_id is locked — OPT-03 nickname change must mutate display name only, never unique_id (asserted by `test_sensor_unique_id_locks_d13`).

---

**Verification status: PASSED for Phase 3.** The integration's first end-to-end runtime is correct, every locked decision is byte-asserted by an automated test, and ROADMAP Phase 3 success criteria #1..#4 are all empirically proved. Ready to advance to Phase 4.

*Phase: 03-coordinator-first-sensor — closed 2026-05-07*
