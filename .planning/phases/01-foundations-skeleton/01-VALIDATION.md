---
phase: 1
slug: foundations-skeleton
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `01-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 9.x (transitive via `pytest-homeassistant-custom-component==0.13.326`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` (no separate `pytest.ini`) |
| **Quick run command** | `uv run pytest -q` (after `uv pip install -r requirements_test.txt`) |
| **Full suite command** | `uv run pytest -v --cov=custom_components.ha_pronote --cov-report=term-missing` |
| **Phase gate command** | `uv run pytest -q && uv run ruff format --check . && uv run ruff check . && npx pyright && uv run codespell` |
| **Estimated runtime** | ~10s (Phase 1 ships only smoke tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q && uv run ruff check . && uv run ruff format --check .` (fast loop, <10s)
- **After every plan wave:** Run `uv run pytest -q && npx pyright && uv run ruff format --check . && uv run ruff check . && uv run codespell` (full local mirror of CI)
- **Before `/gsd-verify-work`:** Phase gate command MUST be green AND at least one PR merged through CI on a feature branch (otherwise success criterion #2 — "CI gates work" — is unverified)
- **Max feedback latency:** ~15s for the full local mirror of CI

---

## Per-Task Verification Map

> Plan/task IDs are placeholders; the planner will pin them when PLAN.md files are written.
> Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-{P}-{T} | repo-skeleton | 1 | DIST-01 | — | manifest.json + hacs.json present and valid | smoke (CI) | `validate.yml` runs `home-assistant/actions/hassfest@<sha>` + `hacs/action@<sha>` | ❌ W0 | ⬜ pending |
| 01-{P}-{T} | repo-skeleton | 1 | DIST-02 | T-1-pin | manifest declares `iot_class=cloud_polling`, `quality_scale=bronze`, runtime requirements pinned | unit | `pytest tests/test_manifest.py -x` | ❌ W0 | ⬜ pending |
| 01-{P}-{T} | ci-workflows | 2 | DIST-03 | T-1-sha | every PR runs lint+validate+test and blocks merge on failure | integration (CI) | branch protection observable on a real PR | ❌ W0 (manual) | ⬜ pending |
| 01-{P}-{T} | tooling-uv | 1 | DIST-08 | — | `uv pip install -r requirements_test.txt && uv run pytest` from clean checkout green | smoke (local + CI) | `pytest -q` exits 0 | ❌ W0 | ⬜ pending |
| 01-{P}-{T} | tooling-uv | 1 | phase-contract | — | `DOMAIN == "ha_pronote"` (folder ↔ manifest match) | unit | `pytest tests/test_init.py::test_domain_constant_is_ha_pronote -x` | ❌ W0 | ⬜ pending |
| 01-{P}-{T} | tooling-uv | 1 | phase-contract | — | placeholder ConfigFlow `async_step_user` aborts cleanly with `reason=not_implemented` | integration (uses `hass` fixture) | `pytest tests/test_init.py::test_config_flow_placeholder_aborts -x` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

> Phase 1 is greenfield. The list below is exhaustive — every test artifact is a Wave 0 gap.

- [ ] `tests/__init__.py` — empty package marker
- [ ] `tests/conftest.py` — `auto_enable_custom_integrations` autouse fixture (`pytest-homeassistant-custom-component`)
- [ ] `tests/test_init.py` — covers DIST-01, DIST-08 + ConfigFlow placeholder contract
- [ ] `tests/test_manifest.py` — asserts `manifest.json` valid JSON, contains `iot_class`, `quality_scale`, `requirements`, `codeowners`, `documentation`, `issue_tracker`, `domain == "ha_pronote"`
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` block
- [ ] `requirements_test.txt` — pinned test deps (`homeassistant==2026.4.4`, `pytest-homeassistant-custom-component==0.13.326`)
- [ ] `.github/workflows/test.yml` — CI test run
- [ ] `.github/workflows/lint.yml` — CI lint run (ruff + pyright + codespell)
- [ ] `.github/workflows/validate.yml` — CI hassfest + hacs/action

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HACS install end-to-end (clone → add custom repo in HACS UI → install → integration appears in HA) | DIST-01 | Requires running HA dev container + HACS frontend; no automated harness for HACS frontend in CI | Bring up `.devcontainer/`, install HACS, add `https://github.com/tom333/ha-pronote` as custom repo, install, restart HA, confirm "HA-Pronote" listed under integrations |
| Branch protection actually blocks merge | DIST-03 | GitHub branch protection is configured in repo settings, not in code | Open a throwaway PR with a deliberately failing test; confirm the PR is not mergeable; close PR |
| Release workflow zips and attaches the asset | DIST-09 (deferred to Phase 7 release tag) | Only triggers on `release: published`; cannot run without cutting a real tag | Cut a `v0.0.1` test tag (or use the workflow_dispatch fallback if added later); confirm `ha_pronote.zip` attaches to the GitHub Release |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
