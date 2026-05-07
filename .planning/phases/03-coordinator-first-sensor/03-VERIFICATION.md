---
phase: 03-coordinator-first-sensor
verified: 2026-05-07T03:00:00Z
status: human_needed
score: 4/4 must-haves verified at code level (CI-blocked test execution)
overrides_applied: 0
re_verification:
  previous_status: phase-level-rollup (non-canonical executor-authored)
  previous_score: GREEN (self-declared by 03-04 executor)
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  note: "Previous 03-VERIFICATION.md was authored by the 03-04 executor as a phase-rollup self-declaration, not by gsd-verifier. This file OVERWRITES it with the canonical verifier output."
gaps: []
human_verification:
  - test: "Live HA install end-to-end — Add Integration -> HA-Pronote -> enter URL/account_type/username/password -> verify entry created, no entry on wrong password, no plain-text password leakage on the form (CR-01 spot-check)"
    expected: "Wrong password produces 'invalid_auth' error in form (no entry persisted). On valid creds, entry appears with title '<child_name> (<account_type>)'. Visual: password field MUST be masked — see CR-01."
    why_human: "Form rendering and password-masking behavior cannot be observed without an HA UI; UI screenshot review explicitly skipped at planning gate per 03-DISCUSSION-LOG.md. Critical because CR-01 is a security defect."
  - test: "Restart HA after first successful add. Verify entry comes back online without prompting for credentials and AUTH-07 device 'home-assistant-{entry_id[:8]}' appears in the user's Pronote app under connected devices"
    expected: "After restart: no UI prompt, sensor.pronote_<child>_lessons_today resumes its numeric state on the next poll. In Pronote app: a connected device named 'home-assistant-<8 hex>' is visible (manually revocable)."
    why_human: "Requires (a) a real Pronote account, (b) a real HA install, (c) login to the Pronote app to inspect connected devices. Cannot be automated."
  - test: "Observe HA logs (or Developer Tools -> Logs) during a coordinator poll cycle and confirm zero 'Detected blocking call to ...' WARNING entries"
    expected: "No 'Detected blocking call' lines emitted by HA's runtime detector during async_setup_entry first_refresh and during the next 30-min polling cadence cycle."
    why_human: "WR-08 makes the automated test (test_no_blocking_calls_during_poll) non-substantive — it patches fetch_all so HA's blocking-call detector has nothing to catch. The empirical proof for ROADMAP SC#3 must come from a live HA log inspection."
  - test: "Run the full HA-side test suite under Python 3.14.2 / HA 2026.4.x in CI: pytest tests/test_init.py tests/test_config_flow.py tests/test_coordinator.py tests/test_sensor.py tests/test_token_persistence.py"
    expected: "All 31 tests pass. Local environment can't run these (Python 3.13.9 vs HA's 3.14.2+ requirement; conftest top-level imports MockConfigEntry which requires PHACC)."
    why_human: "Local env limitation. Phase 1+2 non-HA tests DID run locally (178 passed, 7 documented Phase 4 skips). Phase 3 HA-side tests defer to CI — needs human/CI confirmation that GREEN."
review_findings:
  blockers_relative_to_phase_goal:
    note: "5 BLOCKER findings from 03-REVIEW.md (CR-01..CR-05) are open. None of them prevent the phase GOAL ('user can add account, see live sensor') from being achievable on the happy path. They DO degrade the contract for Phase 4+ (diff baseline, recovery) and ship a security defect (CR-01 password unmasked). The user must decide: ship-as-is or run gap closure."
    items:
      - id: CR-01
        title: "Password rendered in plain text in HA UI"
        affects_must_have: 1
        impact_summary: "Security/UX defect. Must-have #1 ('credentials validate, no entry on wrong password') is functionally satisfied — the rejection path works. But CLAUDE.md mandates 'jamais en clair dans les logs/UI'. Ship-blocker for security posture, NOT for functional goal."
        ship_recommendation: "FIX before shipping — security regression."
      - id: CR-02
        title: "_recover_from_auth_error mis-classifies non-auth failures as auth failures"
        affects_must_have: 2
        impact_summary: "Mid-poll RateLimitedError or CommunicationError during recovery raises ConfigEntryAuthFailed instead of UpdateFailed. Triggers spurious user-facing reauth flow on transient blip. Conflicts with D-22 contract. Phase 5 circuit-breaker reads .reason — silent loss."
        ship_recommendation: "FIX before Phase 5; not a happy-path goal blocker for Phase 3."
      - id: CR-03
        title: "_capture_session runs before _previous_snapshot update — fetch result lost on token-write failure"
        affects_must_have: 3
        impact_summary: "If export_credentials() raises, the snapshot is silently lost AND _previous_snapshot stays stale. Phase 4's diff baseline drifts. Latent: token capture rarely fails today, but the ordering is wrong."
        ship_recommendation: "FIX before Phase 4 lands diff layer; not a happy-path goal blocker for Phase 3."
      - id: CR-04
        title: "client.set_child invoked without typed-error mapping"
        affects_must_have: 2
        impact_summary: "Three call sites (config_flow.py:123, __init__.py:70, coordinator.py:130) call set_child via async_add_executor_job without wrapping in api/client.py's typed-error facade. Raw pronotepy.PronoteAPIError escapes; user sees opaque 'Unknown error'."
        ship_recommendation: "FIX before shipping — degrades the D-04/D-22 error-mapping contract for parent accounts."
      - id: CR-05
        title: "_capture_session swallows pronotepy errors with no exception handling"
        affects_must_have: 2
        impact_summary: "Compounds with CR-03. export_credentials() failures escape unhandled. Half-init clients can KeyError mid-iteration."
        ship_recommendation: "FIX before shipping — combined with CR-03, an export_credentials() blip invalidates a successful poll."
  warnings:
    - "WR-01: entity.py available property breaks CoordinatorEntity._attr_available chain (latent — no current subclass uses _attr_available)."
    - "WR-02: __init__.py async_setup_entry uses raw [] subscript on entry.data — no graceful failure on malformed entry."
    - "WR-03: build_or_resume_client fast-path swallows ALL pronotepy.PronoteAPIError including IP-suspended (would extend ban) — Phase 5 mitigates."
    - "WR-04: _recover_from_auth_error makes a third request to a possibly-banned IP — Phase 5 circuit breaker mitigates."
    - "WR-05: pronotepy error messages logged verbatim — potential credential leakage — Phase 7 diagnostics redaction owner."
    - "WR-06: config_flow._create_entry doesn't bubble set_child errors — degrades D-04 error mapping for parent accounts (relates to CR-04)."
    - "WR-07: async_unload_entry does not stop the coordinator's polling loop — politesse/CLAUDE.md."
    - "WR-08: test_no_blocking_calls_during_poll is NON-SUBSTANTIVE — patches fetch_all away, so HA's detector has nothing to catch. ROADMAP SC#3 thus has no automated empirical guard. Defer to human verification (live HA log inspection)."
---

# Phase 3: Coordinator & First Sensor — Verification Report

**Phase Goal:** User can add a Pronote account via Config Flow and see one live sensor (lessons-today count) updating on the polling interval — the executor boundary, runtime_data plumbing, and entity identity all proven end-to-end.

**Verified:** 2026-05-07
**Status:** human_needed
**Re-verification:** Yes — overwrites a non-canonical executor-authored 03-VERIFICATION.md (which was a self-declared phase-rollup, not gsd-verifier output).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can click "Add Integration" -> HA-Pronote -> enter URL+account_type+username+password -> entry created only if credentials validate; wrong password produces a clear error in the form, no entry persisted | VERIFIED (code) — security WARNING via CR-01 | `config_flow.py:79-86` maps AuthError->invalid_auth (and the other 3 error rows); error path returns `async_show_form` with `errors=` dict — no `async_create_entry` reached; tests `test_user_step_eleve_happy_path` + `test_user_step_error_mapping` (4 parametrized rows) lock the contract. **CR-01 caveat:** the password input is rendered in plain text (no `TextSelector(type=PASSWORD)`) — security defect, but does NOT block must-have #1 functional behavior. |
| 2 | After HA restart, entry comes back online without fresh login (session restored from `client.export_credentials()` stored in `entry.data`); device named `home-assistant-{entry_id[:8]}` visible in Pronote app | VERIFIED (code) — needs live verification | `api/client.py:96-110` token_login fast path with `device_name` kwarg; `__init__.py:44` derives `device_name = f"home-assistant-{entry.entry_id[:8]}"`; `__init__.py:50-60` passes session to `build_or_resume_client` via executor; `coordinator.py:146-153` writes fresh session to `entry.data["session"]` after every successful poll. Tests `test_build_or_resume_client_uses_token_login_when_session_present` + 3 fallback tests cover the helper. **CR-02/CR-03/CR-05 caveats:** the recovery + token-capture paths have ordering and error-classification defects (see review_findings); not a happy-path blocker but the contract degrades on edge conditions. |
| 3 | One sensor `sensor.pronote_<child>_lessons_today` shows a numeric count that refreshes on the configured interval; HA Developer Tools shows zero "Detected blocking call" warnings during a poll | VERIFIED (code) — empirical guard insufficient | `sensor.py:64-69` declares `_attr_unique_id = f"pronote_{...}_lessons_today"` and `native_value = len(self.coordinator.data.lessons_today)`. Test `test_sensor_native_value_equals_lessons_today_count` asserts state == "3" with N=3 lessons today. Every pronotepy call site wraps in `async_add_executor_job` (5 call sites in `coordinator.py`, 2 in `__init__.py`, 3 in `config_flow.py`). **WR-08 caveat:** `test_no_blocking_calls_during_poll` patches `fetch_all` away, so the detector has nothing to catch — the assertion is trivially true regardless of executor wrapping. Empirical SC#3 proof must come from human log inspection on a live HA install. |
| 4 | `unique_id` format is `pronote_{child_identifier}_{sensor_kind}` — frozen and documented in code; `async_migrate_entry` skeleton is present (returns True) so future schema changes preserve entity history | VERIFIED | `sensor.py:64` byte-locks `f"pronote_{entry.runtime_data.child_identifier}_lessons_today"`; `__init__.py:100-107` declares `async_migrate_entry` returning `True`. Tests `test_sensor_unique_id_locks_d13` (entity registry lookup against the byte-exact string `pronote_jean_dupont_lessons_today`) and `test_async_migrate_entry_returns_true` lock both. |

**Score:** 4/4 truths verified at code level. ROADMAP success criterion #3's empirical guard (zero blocking calls during a poll) requires live verification because `test_no_blocking_calls_during_poll` is non-substantive (WR-08).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/ha_pronote/config_flow.py` | Real two-step flow with D-04 error mapping + D-05 unique_id + D-10..D-13 child_identifier freeze | VERIFIED | 170 lines; 5 `async_add_executor_job` calls (build_client + set_child + export_credentials wrappers); ruff/format clean; CR-01 password not masked (security warning). |
| `custom_components/ha_pronote/strings.json` | Phase 3 schema: 4 user-step fields + pick_child + 4 error keys + already_configured abort + lessons_today entity translation_key; legacy `not_implemented` REMOVED | VERIFIED | JSON-valid; top-level keys exactly `{config, entity}`; all 4 error keys present; `not_implemented` confirmed REMOVED via Python parse. |
| `custom_components/ha_pronote/__init__.py` | Real `async_setup_entry` + `async_unload_entry` + `async_migrate_entry` (skeleton); `entry.runtime_data = PronoteData(...)`; NEVER `hass.data[DOMAIN]`; PLATFORMS forwarded both ways; AUTH-07 device_name derived from entry_id; ConfigEntryAuthFailed/ConfigEntryNotReady mapping | VERIFIED | 107 lines; `entry.runtime_data = PronoteData(...)` at line 83; `hass.data[DOMAIN]` count == 0; `f"home-assistant-{entry.entry_id[:8]}"` at line 44; `async_forward_entry_setups` + `async_unload_platforms` both with `PLATFORMS`; `raise ConfigEntryAuthFailed` + `raise ConfigEntryNotReady` both present. WR-02 caveat: raw subscript on entry.data — no graceful failure for malformed entries. WR-07 caveat: async_unload_entry does NOT call `coordinator.async_shutdown()`. |
| `custom_components/ha_pronote/coordinator.py` | `PronoteDataUpdateCoordinator(TimestampDataUpdateCoordinator["Snapshot"])` with `_async_update_data` + `_recover_from_auth_error` + `_capture_session`; D-22 error mapping; D-06 token capture; D-09 silent recovery; C-03 previous_snapshot; D-24 30-min cadence; AUTH-07 device_name in recovery | VERIFIED — with CR-02/CR-03/CR-05 contract gaps | 154 lines; subclass declared at line 54; all 3 methods present; 5 `async_add_executor_job` calls; `update_interval=DEFAULT_REFRESH_INTERVAL`; AUTH-07 device_name at line 125; `self._previous_snapshot` initialized + assigned. **CR-02:** recovery's `except (AuthError, PronoteIntegrationError)` arm at line 141 mis-classifies RateLimitedError + CommunicationError as auth failures. **CR-03:** `_capture_session()` at line 102 runs BEFORE `self._previous_snapshot = snapshot` at line 103 — token-write failure discards the snapshot. **CR-05:** `_capture_session` at lines 146-153 has no exception handling on `export_credentials()`. |
| `custom_components/ha_pronote/data.py` | Plain `@dataclass PronoteData` (NOT frozen) with 5 fields + `type PronoteConfigEntry = ConfigEntry[PronoteData]` | VERIFIED | 39 lines; 5 fields verified; `type` alias present; not frozen (correct — coordinator reassigns `client` on D-09 silent recovery). |
| `custom_components/ha_pronote/entity.py` | `PronoteEntity(CoordinatorEntity[...])` with `_attr_has_entity_name = True` + `device_info` + `available` | VERIFIED — with WR-01 latent bug | 65 lines; class declared with right generic; `_attr_has_entity_name = True`; DeviceInfo with identifiers + name + manufacturer (no model/sw_version/configuration_url per D-17). **WR-01:** `available` property breaks CoordinatorEntity contract — drops `super().available` term; latent bug (no current subclass uses `_attr_available`). |
| `custom_components/ha_pronote/sensor.py` | `async_setup_entry` + `PronoteLessonsTodaySensor(PronoteEntity, SensorEntity)` with frozen unique_id + translation_key matching strings.json + MEASUREMENT state class + mdi:school icon + lessons unit | VERIFIED | 70 lines; reads `entry.runtime_data.coordinator`; class hierarchy correct; `_attr_translation_key = "lessons_today"`; `_attr_icon = "mdi:school"`; `_attr_state_class = SensorStateClass.MEASUREMENT`; `_attr_native_unit_of_measurement = "lessons"`; unique_id format byte-exact; no `_attr_device_class`; no `extra_state_attributes`. |
| `custom_components/ha_pronote/api/client.py` | EXTENDED: `build_or_resume_client(url, account_type, username, password, session, device_name)` with token_login fast path + fresh-login fallback + error mapping; existing `build_client` preserved | VERIFIED — with WR-03 caveat | `build_client` lines 19-58 preserved; `build_or_resume_client` lines 60-130 added; `device_name=device_name` flows into both code paths; api/ stays HA-free. **WR-03 caveat:** fast-path catches ALL `pronotepy.PronoteAPIError` indiscriminately — including "IP suspended" — and falls through to fresh login (extends IP ban). Phase 5 circuit breaker mitigates. |
| `custom_components/ha_pronote/const.py` | EXTENDED: `DEFAULT_REFRESH_INTERVAL: Final = timedelta(minutes=30)` + `PLATFORMS: Final = (Platform.SENSOR,)` | VERIFIED | 23 lines; both new constants present with exact spelling; existing `DOMAIN`, `DEFAULT_SCHOOL_TZ` preserved. |
| `tests/conftest.py` | Phase 1 autouse preserved + 3 MagicMock fixtures (`mock_pronote_client`, `mock_parent_client_two_children`, `mock_config_entry`) + 2 builders | VERIFIED | 135 lines (was 16); all 3 MagicMock fixtures + 2 builder fixtures present. Phase 1 autouse `auto_enable_custom_integrations` preserved (with `yield` -> `return` per ruff PT022). |
| `tests/test_init.py` | Phase 1 placeholder test DELETED; constant smoke test preserved; new tests for `async_setup_entry` happy path + `async_migrate_entry` skeleton | VERIFIED (static) | 3 tests; `test_config_flow_placeholder_aborts` confirmed deleted; `test_domain_constant_is_ha_pronote` preserved; `test_async_setup_entry_happy_path` + `test_async_migrate_entry_returns_true` added. |
| `tests/test_config_flow.py` | NEW; 6 async tests covering D-01..D-05 happy paths + 4-row error mapping + unique_id format + already_configured abort | VERIFIED (static) | 6 test functions; parametrized error mapping covers all 4 rows; unique_id format asserted byte-exact; all patches at config_flow.build_client (C-05 seam). |
| `tests/test_coordinator.py` | NEW; 8 tests covering D-06 token capture + D-20 + D-22 (×3) + D-24 + C-03 + COORD-02 blocking-call detector | VERIFIED (static) — with WR-08 caveat | 8 test functions; all 3 error-mapping rows covered; update_interval == 30 min asserted; previous_snapshot populated asserted. **WR-08:** `test_no_blocking_calls_during_poll` patches `fetch_all` so HA's detector has nothing to catch — the empirical SC#3 guard does NOT actually validate executor wrapping. |
| `tests/test_sensor.py` | NEW; 6 tests covering D-13/D-14/D-15/D-16/ENT-02/ENT-03/TIME-01 sensor contract | VERIFIED (static) | 5 async + 1 sync introspection; native_value asserted == "3"; unique_id byte-exact via entity registry; class attributes locked; no extra_state_attributes asserted; unavailable on coordinator failure asserted. |
| `tests/test_token_persistence.py` | NEW; 8 tests covering D-06/D-07/D-09/AUTH-04/AUTH-07: build_or_resume_client paths + silent-recovery roundtrip | VERIFIED (static) | 7 sync monkeypatch + 1 async coord roundtrip; `device_name` kwarg captured; all 3 fallback exception paths covered; fresh-login error mapping covered; silent-recovery writes new session asserted. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| HA Add-Integration UI | `HaPronoteConfigFlow.async_step_user` | manifest.json `config_flow: true` + `domain: ha_pronote` | WIRED | manifest.json verified via Python parse: `config_flow=True`, `domain=ha_pronote`. |
| `config_flow.async_step_user` | `api.build_client` | `await self.hass.async_add_executor_job(partial(build_client, ...))` | WIRED | config_flow.py:70-78. Executor-wrapped per Pitfall 6. |
| `config_flow._create_entry` | `client.set_child` (parent) + `client.export_credentials` | `async_add_executor_job` | WIRED — with WR-06 caveat | config_flow.py:123 + 156. Both via executor. WR-06: no try/except around set_child — pronotepy errors escape as "Unknown error" abort. |
| `__init__.async_setup_entry` | `build_or_resume_client` | `await hass.async_add_executor_job(partial(build_or_resume_client, ..., device_name))` | WIRED | __init__.py:50-60. AUTH-07 device_name + entry.data session both threaded through. |
| `__init__.async_setup_entry` | `entry.runtime_data = PronoteData(coordinator=..., client=..., child_identifier=..., child_index=..., school_tz=...)` | direct assignment | WIRED | __init__.py:83-89. NOT `hass.data[DOMAIN]` (anti-pattern 6 avoided — verified count == 0). |
| `__init__.async_setup_entry` | sensor platform setup | `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` | WIRED | __init__.py:91. PLATFORMS = (Platform.SENSOR,) verified in const.py. |
| `coordinator._async_update_data` | `fetch_all` | `await self.hass.async_add_executor_job(partial(fetch_all, self._client, today, self._school_tz, self._child_index))` | WIRED | coordinator.py:84-92. |
| `coordinator._capture_session` | `entry.data["session"]` | `self.hass.config_entries.async_update_entry(entry, data={**entry.data, "session": new_session})` | WIRED — with CR-03/CR-05 caveats | coordinator.py:146-153. **CR-03:** runs before `_previous_snapshot = snapshot` so a write failure loses the fresh snapshot. **CR-05:** no exception handling on `export_credentials()`. |
| `sensor.async_setup_entry` | `PronoteLessonsTodaySensor(coordinator, entry)` | `async_add_entities([...])` | WIRED | sensor.py:34-41. Reads `entry.runtime_data.coordinator`. |
| `PronoteLessonsTodaySensor.native_value` | `coordinator.data.lessons_today` | `len(self.coordinator.data.lessons_today)` | WIRED | sensor.py:67-69. Snapshot.lessons_today is the typed property from Phase 2 models. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|---------|
| `PronoteLessonsTodaySensor.native_value` | `self.coordinator.data` (Snapshot) | `_async_update_data` -> `fetch_all` (Phase 2) -> pronotepy `client.lessons(...)` | YES (in production) — tests inject real Snapshot fixtures with N lessons | FLOWING (subject to live HA verification) |
| `entry.data["session"]` | `new_session` from `client.export_credentials()` | pronotepy.Client.export_credentials (executor-wrapped) | YES — but CR-05 means a raise mid-call drops the update silently | FLOWING (with caveat — see CR-05) |
| `entry.runtime_data.coordinator` | `PronoteDataUpdateCoordinator` instance | `__init__.async_setup_entry` direct construction | YES | FLOWING |
| Form errors `errors={"base": <key>}` | exception caught -> error key mapped | `build_client` raises typed exception | YES — all 4 D-04 rows covered | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ruff check (Phase 3 production + test files) | `/home/moi/.local/bin/ruff check custom_components/ha_pronote/ tests/` | "All checks passed!" | PASS |
| ruff format (Phase 3 files only) | `ruff format --check` on the 14 Phase 3 files | "14 files already formatted" | PASS |
| strings.json schema | Python parse → top-level keys, error keys, no `not_implemented` | All assertions pass | PASS |
| manifest.json valid + Phase 3 floor | Python parse → `domain=ha_pronote`, `config_flow=True`, `iot_class=cloud_polling`, `quality_scale=bronze`, `requirements=[pronotepy==2.14.6, python-slugify==8.0.4]` | Conforms to CLAUDE.md tech stack | PASS |
| HA-importing tests (test_init, test_config_flow, test_coordinator, test_sensor, test_token_persistence) | `pytest tests/test_*.py` | SKIPPED — local Python 3.13.9 vs project requires 3.14.2; PHACC unavailable in `.venv` | SKIP — defer to CI |
| Phase 1+2 non-HA tests (test_no_ha_imports, test_manifest, test_fixtures, test_api/, test_diff/) | `pytest` | SKIPPED locally because `tests/conftest.py` now imports `MockConfigEntry` at module scope (PHACC required) | SKIP — defer to CI; per prompt "178 passed, 7 known skips (all documented Phase 4 verification gates)" earlier |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUTH-01 | 03-01 | Configurer compte Pronote via Config Flow UI HA | SATISFIED | config_flow.py:55-95 (`async_step_user` with URL + account_type + username + password); test_user_step_eleve_happy_path |
| AUTH-02 | 03-01 | Valider credentials contre Pronote au moment de la config | SATISFIED | config_flow.py:69-86 (build_client raises -> errors dict, no entry created); test_user_step_error_mapping (4 rows parametrized) |
| AUTH-04 | 03-02 | Persister la session via export_credentials() et rejouer au démarrage | SATISFIED | api/client.py:96-110 token_login fast path + coordinator.py:146-153 capture; test_build_or_resume_client_uses_token_login_when_session_present + test_coordinator_writes_new_session_after_silent_recovery |
| AUTH-07 | 03-02 | device_name = home-assistant-{entry_id[:8]} | SATISFIED | __init__.py:44 + coordinator.py:125; test asserts device_name kwarg captured == "home-assistant-12345678" |
| COORD-01 | 03-02 | DataUpdateCoordinator with runtime_data pattern (no hass.data[DOMAIN]) | SATISFIED | __init__.py:83 (entry.runtime_data = PronoteData); 0 hass.data[DOMAIN] usages |
| COORD-02 | 03-02 | All pronotepy calls in async_add_executor_job (zero blocking calls) | SATISFIED (code) — empirical guard insufficient | All 5 pronotepy calls in coordinator wrapped + 2 in __init__ + 3 in config_flow. **WR-08:** test_no_blocking_calls_during_poll is non-substantive — needs live HA log verification. |
| TIME-01 | 03-03 | Sensor "Emploi du temps" — state = nombre de cours du jour | SATISFIED | sensor.py:67-69 (`return len(self.coordinator.data.lessons_today)`); test_sensor_native_value_equals_lessons_today_count asserts state == "3" |
| ENT-02 | 03-01, 03-03 | unique_id = pronote_{child_identifier}_{sensor_kind} — frozen v1 | SATISFIED | sensor.py:64; child_identifier frozen at flow time per D-10/D-11; test_sensor_unique_id_locks_d13 byte-asserts "pronote_jean_dupont_lessons_today" |
| ENT-03 | 03-01, 03-03 | has_entity_name = True + _attr_translation_key | SATISFIED | entity.py:41 (_attr_has_entity_name = True); sensor.py:52 (_attr_translation_key = "lessons_today"); test_sensor_class_attributes_lock_d15_d16 |
| ENT-04 | 03-02 | async_migrate_entry skeleton (vide v1) | SATISFIED | __init__.py:100-107 (returns True); test_async_migrate_entry_returns_true |

**All 10 requirement IDs accounted for. No orphans (REQUIREMENTS.md maps exactly the same 10 IDs to Phase 3 — verified).**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `config_flow.py` | 50 | `vol.Required("password"): str` (no TextSelector) | BLOCKER (security) | CR-01: password rendered in plain text in HA UI; CLAUDE.md "jamais en clair dans les logs" extends to UI rendering. |
| `coordinator.py` | 102-103 | `_capture_session()` runs before `_previous_snapshot = snapshot` assignment | BLOCKER (correctness) | CR-03: token-write failure discards the freshly-fetched snapshot AND leaves _previous_snapshot stale; Phase 4 diff baseline drifts. |
| `coordinator.py` | 141 | `except (AuthError, PronoteIntegrationError)` collapses RateLimitedError + CommunicationError into auth failures | BLOCKER (incorrect behavior) | CR-02: recovery raises ConfigEntryAuthFailed for non-auth failures; spurious user-facing reauth on transient blip; conflicts with D-22. |
| `coordinator.py` | 146-153 | `_capture_session` has no exception handling on `export_credentials()` | BLOCKER (correctness) | CR-05: an export_credentials() raise propagates to HA's safety net; combined with CR-03, invalidates a successful poll. |
| `__init__.py:70`, `coordinator.py:130`, `config_flow.py:123` | — | `client.set_child` invoked without typed-error mapping wrapper | BLOCKER (incorrect error handling) | CR-04: raw pronotepy.PronoteAPIError escapes the typed-exception facade; user sees opaque "Unknown error". |
| `entity.py` | 62-64 | `available` property drops `super().available` term | WARNING (latent) | WR-01: breaks CoordinatorEntity contract; future _attr_available subclasses will be ignored. |
| `__init__.py` | 53-56,76,86 | Direct subscript on `entry.data["..."]` | WARNING | WR-02: KeyError on malformed entry instead of clean ConfigEntryNotReady. |
| `api/client.py` | 107 | Fast-path catches ALL `pronotepy.PronoteAPIError` including IP-suspended | WARNING (relates Phase 5) | WR-03: would hammer a banned IP with fresh-login retry, extending the ban. Phase 5 circuit breaker mitigates. |
| `coordinator.py` | 106-144 | Recovery makes a third request to a possibly-banned IP without cooldown | WARNING (relates Phase 5) | WR-04: violates CLAUDE.md "politesse polling" on aliased exception loop. Phase 5 mitigates. |
| `coordinator.py:98,100,142`, `api/client.py:48,50-55,121,123-128` | — | pronotepy error messages logged verbatim into UpdateFailed/ConfigEntryAuthFailed | WARNING (relates Phase 7) | WR-05: potential credential leakage in logs; CLAUDE.md "jamais en clair dans les logs". Phase 7 owns redaction. |
| `config_flow.py` | 113-170 | `_create_entry` does not bubble set_child errors back as form errors | WARNING (relates CR-04) | WR-06: degrades D-04 error-mapping contract for parent accounts. |
| `__init__.py` | 95-97 | `async_unload_entry` does not call `coordinator.async_shutdown()` | WARNING (politesse) | WR-07: post-unload polling fires once; CLAUDE.md "politesse polling". |
| `tests/test_coordinator.py` | 144-170 | `test_no_blocking_calls_during_poll` patches `fetch_all` — non-substantive | WARNING (test quality) | WR-08: detector has nothing to catch; ROADMAP SC#3 lacks an automated empirical guard. |

### Human Verification Required

#### 1. Live config-flow add + password masking visual check (CR-01 spot-check)

**Test:** Add HA-Pronote integration via the HA UI. Type a password into the form.
**Expected:** Password field MUST be masked (dots/circles, not plain text). Wrong password produces an `invalid_auth` error in the form (no entry created). Valid password creates an entry with the title `<child_name> (<account_type>)`.
**Why human:** Form rendering and password-masking behavior cannot be observed without an HA UI. UI screenshot review was explicitly skipped at planning gate per `03-DISCUSSION-LOG.md`. **Critical because CR-01 is an open security defect** — confirmation that the password is unmasked on screen is the trigger for closure.

#### 2. HA restart + Pronote app device list verification (must-have #2 SC#2)

**Test:** After first successful add, restart HA. Open the user's Pronote app, navigate to the connected-devices section. Wait for the next coordinator poll cycle (~30 min, or trigger manual refresh via HA Developer Tools → Service `homeassistant.update_entity`).
**Expected:** After restart: no UI prompt for credentials, `sensor.pronote_<child>_lessons_today` resumes its numeric state on the next poll. In the Pronote app: a device named `home-assistant-<8 hex>` is visible (where `<8 hex>` matches `entry.entry_id[:8]`) — manually revocable from there.
**Why human:** Requires (a) a real Pronote account, (b) a real HA install, (c) login to the Pronote app to inspect connected devices. Cannot be automated.

#### 3. Live blocking-call detector log inspection (ROADMAP SC#3 empirical guard)

**Test:** Start HA with the integration set up. Watch the HA logs (Developer Tools → Logs, level INFO+) during `async_setup_entry`'s first refresh AND during the next 30-min polling cadence cycle.
**Expected:** Zero `Detected blocking call to ...` WARNING entries.
**Why human:** WR-08 makes the automated test (`test_no_blocking_calls_during_poll`) non-substantive — it patches `fetch_all` so HA's blocking-call detector has nothing to catch. The empirical proof for ROADMAP SC#3 must come from a live HA log inspection. Alternatively, tighten the test to exercise a real blocking call path (per WR-08 fix recommendation).

#### 4. Full HA-side test suite execution under Python 3.14.2 / HA 2026.4.x (CI gate)

**Test:** In CI (or a properly-bootstrapped Python 3.14.2 venv with `pytest_homeassistant_custom_component==0.13.326` installed), run:
```
pytest tests/test_init.py tests/test_config_flow.py tests/test_coordinator.py tests/test_sensor.py tests/test_token_persistence.py
```
**Expected:** All 31 tests pass.
**Why human:** Local environment limitation — the project requires Python 3.14.2+ but the local venv is 3.13.9 + missing PHACC. The static checks (ruff, format, JSON parse, grep anchors) ALL pass; only the runtime execution defers to CI.

### Gaps Summary

**No gaps blocking the phase GOAL on the happy path.** All 4 must-haves are verified at the code level. Every artifact exists, every key wiring link is in place, every requirement ID is accounted for, ruff + format + JSON validation all pass.

**However, the phase ships with 5 BLOCKER-class defects and 8 WARNINGs from `03-REVIEW.md` that the user must triage before declaring Phase 3 closed.**

The decision tree:
- **Ship as-is** → ROADMAP SC#1-#4 are functionally satisfied for the happy path; Phase 4 can build on the existing seam. Risk: CR-01 (password unmasked) is a security regression that should not ship to users; CR-02..CR-05 will complicate Phase 4's diff layer + Phase 5/6 reauth flows.
- **Run gap closure** → Address CR-01 + CR-02 + CR-03 + CR-04 + CR-05 before Phase 4. The fixes are well-specified in `03-REVIEW.md`; estimated effort is small (1 plan, ~20 minutes scope).

**Recommendation:** Run gap closure on **CR-01 (password masking — security regression)** at minimum before shipping to any user. CR-02..CR-05 can be addressed within Phase 3 OR deferred to a Phase 3.5 "code review fixup" plan; either way they should land before Phase 4 starts.

### Deferred Items (Step 9b filter)

The following review WARNINGs map to later phases of this milestone and are NOT counted as Phase 3 gaps:

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | WR-03 — IP-suspended fast-path swallow + WR-04 — recovery hammers banned IP | Phase 5 | Phase 5 success criteria: "IP-ban circuit breaker"; goal: "the integration cannot get the user's IP banned even under misconfiguration" |
| 2 | WR-05 — pronotepy error messages logged verbatim (potential credential leakage) | Phase 7 | Phase 7 goal: "Diagnostics with redaction"; CLAUDE.md "Phase 7 ships diagnostics redaction" |
| 3 | CR-02 spurious reauth flow on transient errors (loss of D-22 .reason signal needed by Phase 5) | Phase 5 / Phase 6 | Phase 5 reads `.reason` for backoff (per coordinator.py:97 comment); Phase 6 owns AUTH-03 reauth lifecycle |

CR-01, CR-03, CR-04, CR-05, WR-01, WR-02, WR-06, WR-07, WR-08 are NOT addressed by any later phase — they are real Phase 3 review findings that need a closure decision.

---

_Verified: 2026-05-07_
_Verifier: Claude (gsd-verifier)_
