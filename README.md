# HA-Pronote

Home Assistant custom integration for Pronote (French school management system).

> **Status:** Early development. The integration installs but does not yet
> create entities. See [ROADMAP.md](.planning/ROADMAP.md) for the planned
> feature timeline.

## Installation (HACS custom repository)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → top-right menu → **Custom repositories**.
3. Add `https://github.com/tom333/ha-pronote` with category **Integration**.
4. Install **HA-Pronote** from the HACS catalogue.
5. Restart Home Assistant.

Account configuration via the UI ships in a future release.

## Requirements

- Home Assistant 2026.4.0 or later
- Python 3.14.2 (managed by HA — not user-facing)

## License

See [LICENSE](LICENSE).
