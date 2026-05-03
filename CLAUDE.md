<!-- GSD:project-start source:PROJECT.md -->
## Project

**HA-Pronote — Intégration Home Assistant pour Pronote**

Composant personnalisé Home Assistant qui intègre Pronote pour exposer notes, emploi du temps et notifications scolaires sous forme d'entités HA (sensors). Il permet aux familles de centraliser le suivi scolaire dans leur tableau de bord domotique et de déclencher des automatisations (alertes changement d'EDT, nouvelles notes, nouvelles informations). Distribué via HACS en custom repository.

**Core Value:** L'utilisateur reçoit une notification fiable et exploitable dès qu'un cours est annulé ou modifié pour le jour même ou le lendemain. C'est l'usage qui justifie l'existence du projet — le reste (notes, notifs) en découle.

### Constraints

- **Tech stack** : Python 3 (standard HA), gestion projet avec `uv`, dépendance principale `pronotepy`, architecture `DataUpdateCoordinator` (async HA)
- **Distribution** : Format `custom_components/` conforme HACS (manifest.json, hacs.json, structure standard)
- **Politesse polling** : Intervalle paramétrable (défaut 30 min, choix 15/30/60), surveillance accrue 17h–20h pour le lendemain — éviter bannissement IP du serveur école
- **Lecture seule** : Aucune écriture vers Pronote (sécurité + risque ban)
- **Compatibilité HA** : Versions récentes de Home Assistant (à figer dans `manifest.json` au début de l'implémentation)
- **Qualité** : Couverture tests complète (unitaires + intégration mockée `pronotepy`) + CI GitHub Actions dès la v1
- **Sécurité credentials** : Identifiants Pronote stockés via mécanisme de stockage HA standard, jamais en clair dans les logs
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Executive Summary
- **Pronote client = `pronotepy 2.14.6`**. There is no async fork, no `pronotelib`, no Python `pawnote`. The maintainer put the project in **maintenance mode in 2026** and recommends JS/TS alternatives — irrelevant for HA, where Python is mandatory. Decision: ship on `pronotepy`, accept it is sync-only, and isolate it behind an executor boundary.
- **Home Assistant 2026.3+ requires Python 3.14.2**. There is no escape — HA Core master is `requires-python>=3.14.2` since 2026.3.0 (March 2026). Targeting an older HA to dodge Python 3.14 is a self-inflicted wound; users on 2026.x will not install you.
- **Tooling = ruff (lint+format) + pyright + pytest + uv**. Black, mypy, flake8, isort, pip-tools, poetry are all out. This matches both HA Core (`pyproject.toml`) and the modern HACS blueprint (`jpawlowski/hacs.integration_blueprint`, last push 2026-04-27).
- **Tests = `pytest-homeassistant-custom-component`** (auto-tracks HA Core daily, currently `0.13.326` for HA `2026.5.0b0`).
- **CI = `home-assistant/actions/hassfest@master` + `hacs/action@main`**, both pinned by SHA. Tag versions on those repos are stale (`22.5.0`, `1.0.0`) and unused by the community.
## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | `>=3.14.2` | Runtime | HA 2026.3+ enforces it (`REQUIRED_PYTHON_VER = (3, 14, 2)` in `homeassistant/const.py`). Going lower locks you out of current HA. |
| **Home Assistant Core** | `>=2026.3.0` (target `2026.4.x` for floor) | Host platform | First version requiring Py 3.14.2. Targeting `2026.4` gives you a stable production HA + matches the `jpawlowski` blueprint. Bump the floor in `hacs.json` only when you start using a new API. |
| **`pronotepy`** | `==2.14.6` | Pronote API client | Only viable Python wrapper. Last release 2026-03-22, repo active for bugfixes. **Sync only** (uses `requests`). Pin to exact version — Pronote breaks the API regularly and `pronotepy` ships compensating fixes. |
| **`DataUpdateCoordinator`** | bundled with HA | Polling orchestration | Standard HA pattern for cloud-polling integrations (`iot_class: cloud_polling`). Use the **`TimestampDataUpdateCoordinator`** subclass (added in HA 2024.x, used in `delphiki/hass-pronote`) — it tracks `last_update_success_time` automatically, useful for the "EDT changed since last poll" comparison. |
| **`ConfigFlow`** + `OptionsFlow` | bundled with HA | UI setup + per-entry options | Required for HACS quality. The polling interval and 17h–20h window must live in `OptionsFlow`, not `data` (so users can change them without re-auth). |
### Supporting Libraries (runtime — declared in `manifest.json` `requirements`)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pronotepy` | `==2.14.6` | Pronote scraping | Always — single dep. |
| `python-slugify` | `==8.0.4` | Slugify child names for entity IDs | Likely needed for multi-account naming (`sensor.pronote_alice_grades`). Same version pinned in HA Core's `pyproject.toml` so no conflict. |
### Development & Test Stack (declared in `pyproject.toml` / `requirements_test.txt`, **not** `manifest.json`)
| Tool | Version (May 2026) | Purpose | Notes |
|------|--------------------|---------|-------|
| `uv` | `>=0.9.3` | Package manager + venv | 10–100× faster than pip; `uv pip install -r requirements_test.txt` is the bootstrap pattern in 2026 HA dev. |
| `homeassistant` | `==2026.4.4` (or pin to your target floor) | Run tests against a real HA | Pulled transitively by `pytest-homeassistant-custom-component`, but pin explicitly so CI is reproducible. |
| `pytest-homeassistant-custom-component` | `==0.13.326` | Provides `hass` fixture, `MockConfigEntry`, snapshot helpers, `enable_custom_integrations` | Auto-published daily against latest HA (incl. betas). Patch version follows HA, minor version follows internal extraction logic. |
| `pytest` | `==9.0.3` (transitive) | Test runner | Pulled by `pytest-homeassistant-custom-component`. Don't override. |
| `pytest-asyncio` | `==1.3.0` (transitive) | Async test support | **Configure `asyncio_mode = "auto"`** in `pyproject.toml` — required by `pytest-homeassistant-custom-component`. |
| `pytest-cov` | `==7.1.0` (transitive) | Coverage | Standard. |
| `pytest-timeout` | `==2.4.0` (transitive) | Kill hung tests | Helpful when mocking pronotepy. |
| `freezegun` | `==1.5.5` (transitive) / `pytest-freezer 0.4.9` | Mock `datetime.now()` | Critical for testing the "17h–20h heightened polling" logic. |
| `syrupy` | `==5.1.0` (transitive) | Snapshot testing | Standard pattern in HA Core for entity state/attribute snapshots. Use `HomeAssistantSnapshotExtension`. |
| `respx` | `==0.23.1` (transitive) | `httpx` mocking | Probably not needed (pronotepy uses `requests`, not httpx) — but available. |
| `requests-mock` | `==1.12.1` (transitive) | `requests` mocking | Useful for **hermetic pronotepy tests** without going through demo Pronote. Mock at the `requests.Session` level. |
| `ruff` | `==0.15.1` | Lint **and** format | Single tool replaces black + isort + flake8. Match HA Core's `pyproject.toml` `[tool.ruff]` block (the `jpawlowski` blueprint copies it verbatim). |
| `pyright` | latest (via npm `package.json`) | Type checking | HA Core uses `mypy`; the modern HACS blueprint uses `pyright` because it has better incremental performance and runs from `node_modules`. Either works — `pyright` matches the 2026 blueprint trend. |
| `pre-commit` (or `prek`) | `>=4.x` (`prek 0.2.28` in HA Core) | Git hooks | Run `ruff format` then `ruff check --fix` then `pyright`. `prek` is the Rust-rewritten drop-in replacement HA Core adopted in 2025. |
| `codespell` | `==2.4.1` | Spell check | Standard HA hook; cheap insurance for French/English mixed docstrings. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Bootstrap venv, install deps, sync `requirements*.txt` | `uv venv .local/ha-venv --python 3.14 && uv pip install -r requirements_test.txt`. Cache `.local/ha-venv` in CI. |
| `hassfest` | HA-side validation (manifest schema, requirements, services, translations) | Run via `home-assistant/actions/hassfest@master` in CI. **Mandatory** for HACS. |
| `hacs/action` | HACS-side validation (`hacs.json`, repo structure, brand assets) | Run via `hacs/action@main` with `category: integration`. Use `ignore: brands` until you submit brand images to `home-assistant/brands`. |
| `release-please` (Google) or `softprops/action-gh-release` | Tag-driven release + zip bundling | Two patterns in the wild: (1) `release-please` for full automation (used by `jpawlowski` blueprint), (2) manual GitHub release → workflow injects `tag_name` into `manifest.json` `version` and zips `custom_components/pronote/` into `pronote.zip` (used by `delphiki/hass-pronote`). The second is simpler for v1. |
| `actions/setup-python@v6` | Pin Python 3.14 in CI | Standard. |
| `astral-sh/setup-uv@v8` | Install uv in CI with cache | Cache key on `**/requirements*.txt`. |
| `actions/cache@v5` | Cache the HA venv (`.local/ha-venv`) | Saves ~90s per CI run on `pip install homeassistant` (HA has many heavy deps). |
## Installation
# Bootstrap (one-time)
# Runtime deps (declared in manifest.json + mirrored in requirements.txt for reference)
# Test deps (note: pulls homeassistant 2026.4.x + the entire HA test toolchain)
# Dev convenience (ruff is needed for pre-commit)
# Type checker (via npm — matches blueprint pattern)
# Hooks
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `pronotepy` (sync, maintenance mode) | `pawnote` / Blocksnote (JS/TS) | Only if you rewrite the whole integration as a Node.js sidecar HA addon. Not realistic for a `custom_component`. |
| `pronotepy` direct | Fork `pronotepy` and add async | Only if `pronotepy` becomes unmaintained and breaks. Today it's actively bugfixed (last commit 2026-04-24) — forking is premature. |
| Python 3.14 floor | Python 3.13 floor (HA 2026.1–2026.2) | Only if you must support HA users stuck on `2026.1` or `2026.2` (Feb 2026). For a v1 shipping mid-2026, target current HA. |
| `TimestampDataUpdateCoordinator` | Plain `DataUpdateCoordinator` | Plain coordinator works, but you lose `last_update_success_time` which simplifies your "EDT changed since last poll for J / J+1" diff logic. |
| `ruff` (lint+format) | `black` + `flake8` + `isort` | None — HA Core dropped this combo in 2024. New blueprints don't ship it. |
| `pyright` | `mypy` | `mypy` is fine and is what HA Core uses (`mypy==1.19.1`). Pick `pyright` only if you want the modern blueprint's pattern + faster incremental checks. |
| `uv` | `pip` / `poetry` / `pip-tools` | None — `uv` is now the de-facto manager for HA dev (HA Core itself can be installed via uv since 2024). Poetry adds friction with HA's `requirements*.txt` model. |
| Manual release workflow | `release-please` | If you don't want to learn `release-please` config in v1, use the simpler `delphiki`-style release workflow. Migrate later. |
| `pytest-homeassistant-custom-component` | Hand-rolled HA test harness | Don't. PHACC is auto-regenerated daily against HA, hand-rolling means breaking with every HA release. |
| `requests-mock` for pronotepy tests | Real Pronote demo instance | Demo instance is unreliable for CI (rate limits, intermittent down). Use `requests-mock` against captured fixtures. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Calling `pronotepy` directly from coordinator's `_async_update_data`** | `pronotepy` blocks on `requests`. HA will log "Detected blocking call" and may refuse to start in newer versions. | Wrap **every** call: `await self.hass.async_add_executor_job(client.lessons, today, today + delta)`. See `delphiki/hass-pronote/coordinator.py` for the canonical pattern (26 wrapped calls). |
| **`async_timeout` package** | Banned-API in modern HA Core ruff config. | `asyncio.timeout()` (stdlib, Python 3.11+). |
| **`pytz`** | Banned-API in HA Core ruff config; deprecated. | `zoneinfo.ZoneInfo("Pacific/Noumea")` for the Nouméa locale. |
| **`requests` directly in your code** | Sync HTTP in async loop = same problem as pronotepy. Plus you'd be reimplementing what pronotepy does. | Stick to `pronotepy` for Pronote calls. If you need extra HTTP, use `aiohttp` via `homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)`. |
| **`pronotepy` features beyond what `manifest.json` declares** | Adding deps later = breaking change for users (HACS triggers re-install of deps). | Pin runtime deps in `manifest.json` from day 1. |
| **`black` + `flake8` + `isort` toolchain** | Replaced by `ruff` in HA Core 2024+ and the modern HACS blueprint. Three tools, slow, redundant config. | `ruff format` + `ruff check`. |
| **`mypy --strict`** | HA Core itself doesn't pass strict mypy on integrations. You'll fight false positives forever. | `pyright basic` mode (matches blueprint) or `mypy` with HA Core's per-file ignores. |
| **`pip install` in CI for HA** | Slow (HA pulls 200+ deps including SQLAlchemy, numpy, paho-mqtt). | `uv pip install` + `actions/cache` on `.local/ha-venv` keyed by `requirements*.txt` hash. |
| **`hacs/action@22.5.0` (the latest tag)** | The repo's tags are stale (last tag 2022). Community pins by SHA on `main`. | `uses: hacs/action@<sha> # main`, with renovate/dependabot to bump. |
| **`home-assistant/actions/hassfest@v1.0.0`** | Same: tag is from 2020. Unused. | `uses: home-assistant/actions/hassfest@<sha> # master`. |
| **Hard-coding the `katiramona.ac-noumea.nc` URL** | Even if the project is your personal use case, ConfigFlow must accept any URL — otherwise you can't reuse, can't share, and the integration fails HACS quality scoring later. | ConfigFlow text field + URL validator (use `voluptuous.Url()`). The NC scope is a Pitfall/test-fixture concern, not a stack constraint. |
| **`ENT` modules from `pronotepy.ent`** | Out of scope per `PROJECT.md` (direct Pronote login only in v1). Importing them silently bloats the bundle. | Use `pronotepy.Client(...)` (or `Client.token_login(...)`) directly with username/password. |
| **`aiohttp.ClientSession()` you create yourself** | Leaks sessions, breaks under HA's connection pooling. | `homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)` — but again, you don't need this for `pronotepy`. |
| **`async_add_job` (deprecated)** | Replaced by `async_add_executor_job` since 2022. | `hass.async_add_executor_job(sync_callable, *args)`. |
## Stack Patterns by Variant
- Set `homeassistant: "2026.1.0"` in `hacs.json` instead of `2026.4.0`
- Set `requires-python = ">=3.13.2"` in `pyproject.toml`
- Set `target-version = "py313"` in `[tool.ruff]`
- **Risk:** these versions reach EOL in mid-2026. Not recommended for a project starting May 2026.
- Add `quality_scale` to `manifest.json` (start with `"quality_scale": "bronze"`).
- Submit brand assets to `home-assistant/brands` (icon.png + logo.png) and remove `ignore: brands` from the `hacs/action` step.
- Add full translations under `custom_components/pronote_nc/translations/` (at minimum `en.json` and `fr.json`).
- Convert `release-please` if you used the manual zip pattern in v1.
- **Do NOT** monkey-patch in your component (will break on every `pronotepy` upgrade).
- Open a bug-report-not-feature-request issue at `bain3/pronotepy` (the README explicitly says no new feature PRs in maintenance mode, but bugs are accepted).
- For "the field exists but isn't exposed" — write a thin reader on top of `client.communication.post(...)` (the low-level method delphiki uses on line 528 of `clients.py`).
- This is **expected** (it's the #1 reason this stack exists with full mocked tests).
- Bump `pronotepy==2.14.X` in `manifest.json` to the patched version.
- Your mocked tests stay green; your `requests_mock` fixtures need updating only if Pronote's response shape changes (rare — usually pronotepy absorbs the change).
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `homeassistant==2026.4.4` | `python>=3.14.2` | Hard requirement (`REQUIRED_PYTHON_VER`). |
| `homeassistant==2026.4.4` | `pytest-homeassistant-custom-component==0.13.326` | PHACC tracks HA daily; `0.13.326` was generated for HA `2026.5.0b0` and is backwards-compatible with `2026.4.x`. |
| `pronotepy==2.14.6` | `python>=3.8` | Compatible with Python 3.14, but pulls `requests`, `beautifulsoup4`, `pycryptodome`, `autoslot` — all already in HA Core's transitive deps **except `autoslot`**. HA will install `autoslot` from your `manifest.json` requirements. |
| `pronotepy==2.14.6` | `requests>=2.22.0` | HA Core ships `requests` already. No conflict. |
| `pronotepy==2.14.6` | `pycryptodome>=3.9.4` | HA Core ships `pycryptodome` already. No conflict. |
| `python-slugify==8.0.4` | HA Core | Exact version pinned by HA Core in `pyproject.toml`. Match it to avoid resolver thrash. |
| `ruff==0.15.1` | `python>=3.14` | Set `target-version = "py314"`. Earlier ruff versions don't fully support 3.14 syntax. |
| `hacs/action@main` | `hacs.json` schema | Action validates the `hacs.json` keys listed in [HACS publish docs](https://www.hacs.xyz/docs/publish/start/). Run locally with `act` if needed. |
| `home-assistant/actions/hassfest@master` | `manifest.json` schema | Validates required keys: `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version` (+ optional `config_flow`, `iot_class`, `integration_type`, `requirements`, `dependencies`, `loggers`, `quality_scale`). |
## Key Architectural Decision: pronotepy is sync — how to handle it
- Zero `async def` in `pronotepy`.
- Zero imports of `aiohttp` or `asyncio`.
- All HTTP goes through `requests.Session` (line ~528: `def post(self, ...)` is sync).
- There is no `Client.async`, no `AsyncClient`, no `pronotepy.aio` namespace.
# In coordinator.py
## Sources
- [PyPI: pronotepy](https://pypi.org/pypi/pronotepy/json) — verified `2.14.6`, released 2026-03-22, requires Python `>=3.8`, deps `beautifulsoup4>=4.8.2 / pycryptodome>=3.9.4 / requests>=2.22.0 / autoslot>=2022.12.1`. **HIGH**
- [GitHub: bain3/pronotepy](https://github.com/bain3/pronotepy) — README banner confirms maintenance mode, last commit 2026-04-24, 230 stars, active for bugfixes. Source inspection of `pronotepy/clients.py` confirmed zero async support. **HIGH**
- [PyPI: homeassistant](https://pypi.org/pypi/homeassistant/json) — verified `2026.4.4`, released 2026-04-24, requires `>=3.14.2`. Historical scan: 3.13.2 floor in 2026.1–2026.2, 3.14.2 floor since 2026.3.0. **HIGH**
- [HA Core `homeassistant/const.py`](https://raw.githubusercontent.com/home-assistant/core/master/homeassistant/const.py) — `REQUIRED_PYTHON_VER: Final[tuple[int, int, int]] = (3, 14, 2)`. **HIGH**
- [HA Core `pyproject.toml`](https://raw.githubusercontent.com/home-assistant/core/master/pyproject.toml) — confirmed `requires-python = ">=3.14.2"`, ruff is the formatter+linter, `python-slugify==8.0.4` pinned. **HIGH**
- [HA Core `requirements_test.txt`](https://raw.githubusercontent.com/home-assistant/core/master/requirements_test.txt) — `mypy==1.19.1`, `pylint==4.0.5`, `pytest 9.x`, `prek==0.2.28`. **HIGH**
- [HA Core `.pre-commit-config.yaml`](https://raw.githubusercontent.com/home-assistant/core/master/.pre-commit-config.yaml) — `ruff-pre-commit v0.15.1`, codespell, zizmor. **HIGH**
- [PyPI: pytest-homeassistant-custom-component](https://pypi.org/pypi/pytest-homeassistant-custom-component/json) — verified `0.13.326`, released 2026-04-30, tracks `homeassistant==2026.5.0b0`. Pulls full HA test toolchain (`pytest 9.0.3`, `pytest-asyncio 1.3.0`, `syrupy 5.1.0`, `respx 0.23.1`, `freezegun 1.5.5`). **HIGH**
- [GitHub: MatthewFlamm/pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) — README confirms daily auto-update against HA Core, requires `asyncio_mode = "auto"`. 100 stars, last push 2026-04-30. **HIGH**
- [HA Developer Docs: integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/) — required keys (`domain`, `name`, `codeowners`, `documentation`, `version` for custom integrations), `iot_class`, `config_flow`, `integration_type`, `requirements`. **HIGH**
- [HACS publish/start docs](https://www.hacs.xyz/docs/publish/start/) — `hacs.json` schema (name required; `content_in_root`, `zip_release` + `filename`, `homeassistant`, `hacs`, `country`, `persistent_directory` optional). **HIGH**
- [HACS publish/integration docs](https://www.hacs.xyz/docs/publish/integration/) — confirms `manifest.json` minimum keys for HACS-distributed integrations. **HIGH**
- [GitHub: delphiki/hass-pronote](https://github.com/delphiki/hass-pronote) — reference implementation (94 stars, last push 2026-03-20). Inspected `manifest.json`, `hacs.json`, `__init__.py`, `coordinator.py`, `.github/workflows/`. Confirms `pronotepy==2.14.5` is in production today, `iot_class: cloud_polling`, `TimestampDataUpdateCoordinator`, 26 `async_add_executor_job` call sites. **HIGH**
- [GitHub: jpawlowski/hacs.integration_blueprint](https://github.com/jpawlowski/hacs.integration_blueprint) — modern 2026 HACS blueprint (last push 2026-04-27). Inspected `pyproject.toml`, `manifest.json` (`integration_type: hub`, no version key error), `hacs.json` (`homeassistant: 2026.4.0, hacs: 2.0.5`), `.github/workflows/{lint,validate}.yml`. Source of the `requires-python = ">=3.14"`, `target-version = "py314"`, `pyright` instead of `mypy`, uv-based bootstrap pattern. **HIGH**
- [GitHub: hacs/action releases](https://github.com/hacs/action) — latest tag `22.5.0` (2022-05). Community pins `@main` by SHA. **HIGH** (verified via API)
- [GitHub: home-assistant/actions](https://github.com/home-assistant/actions) — latest tag `1.0.0` (2020-04). Used as `@master` by SHA. **HIGH** (verified via API)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
