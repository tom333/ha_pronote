"""One-shot real-Pronote spike + anonymizer (D-13).

Not a tested production code surface. Lives outside custom_components/.
Reads .env (D-14), invokes api.build_client + api.fetch_all, writes:
  - tests/fixtures/real/_raw_<scenario>_<phase>.json   (gitignored)
  - tests/fixtures/real/<scenario>_<phase>.json        (anonymized, committed)

Anonymization (C-03): explicit name-list, recursive walk, NO regex.
Smoke test (`tests/test_scripts/test_snapshot.py`) covers the deterministic
behavior of `walk_and_replace` and the `no_pii` invariant — NOT the network
round-trip (D-13).
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

# scripts/ is OUTSIDE custom_components/ — direct sys.path tweak so the
# script runs from a fresh checkout without `uv pip install -e .` (D-13).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from custom_components.ha_pronote.api import build_client, fetch_all  # noqa: E402

SCENARIOS = ("cancellation", "room_change", "teacher_swap")
PHASES = ("T0", "T1")


def _read_env(path: Path) -> dict[str, str]:
    """Manual .env parser — no python-dotenv runtime dep (D-13)."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if not sep:
            continue
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def walk_and_replace(obj: Any, replacements: dict[str, str]) -> Any:
    """C-03: explicit name-list, recursive walk. NOT regex."""
    if isinstance(obj, str):
        for old, new in replacements.items():
            obj = obj.replace(old, new)
        return obj
    if isinstance(obj, dict):
        return {k: walk_and_replace(v, replacements) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_and_replace(v, replacements) for v in obj]
    return obj


def anonymize(snapshot_dict: dict, replacements: dict[str, str]) -> dict:
    """Deterministic — same input + same replacements -> same output."""
    return walk_and_replace(snapshot_dict, replacements)


def no_pii(obj: Any, pii_blocklist: list[str]) -> bool:
    """`<specifics>` line 213 invariant — no PII string in serialized form."""
    serialized = json.dumps(obj, ensure_ascii=False)
    return not any(needle in serialized for needle in pii_blocklist if needle)


def _build_replacements(env: dict[str, str]) -> dict[str, str]:
    """D-12: child names, school URL, establishment, teacher names.

    EXTEND this dict with real teacher names and classroom IDs as the spike
    captures them. The `replacements` dict is the source of truth — every
    PII token discovered during the spike MUST be added here BEFORE
    committing the anonymized fixture.
    """
    repls: dict[str, str] = {}
    if env.get("PRONOTE_USERNAME"):
        repls[env["PRONOTE_USERNAME"]] = "Eleve Test"
    if env.get("PRONOTE_URL"):
        host = urlparse(env["PRONOTE_URL"]).netloc
        if host:
            repls[host] = "pronote.example.fr"
    # Plan 02-02's spike executor adds firstname/lastname/teacher names/classroom IDs here.
    return repls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("One-shot Pronote snapshot + anonymizer. Reads .env (D-14). Output goes to tests/fixtures/real/."),
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=SCENARIOS,
        help="Which spike scenario this snapshot represents.",
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=PHASES,
        help="T0 = before the change happened in Pronote; T1 = after.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tests/fixtures/real"),
        help="Output directory (default: tests/fixtures/real/).",
    )
    args = parser.parse_args(argv)

    env = _read_env(REPO_ROOT / ".env")
    for required in (
        "PRONOTE_URL",
        "PRONOTE_USERNAME",
        "PRONOTE_PASSWORD",
        "PRONOTE_ACCOUNT_TYPE",
    ):
        if not env.get(required):
            print(
                f"error: {required} not set in .env (see .env.example)",
                file=sys.stderr,
            )
            return 2

    client = build_client(
        url=env["PRONOTE_URL"],
        account_type=env["PRONOTE_ACCOUNT_TYPE"],  # type: ignore[arg-type]
        username=env["PRONOTE_USERNAME"],
        password=env["PRONOTE_PASSWORD"],
    )
    snap = fetch_all(
        client,
        today=date.today(),
        school_tz=ZoneInfo("Pacific/Noumea"),
    )

    args.out.mkdir(parents=True, exist_ok=True)
    raw_path = args.out / f"_raw_{args.scenario}_{args.phase}.json"
    anon_path = args.out / f"{args.scenario}_{args.phase}.json"

    snap_dict = snap.to_dict()
    raw_path.write_text(
        json.dumps(snap_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    replacements = _build_replacements(env)
    anon = anonymize(snap_dict, replacements)
    anon_path.write_text(
        json.dumps(anon, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not no_pii(
        json.loads(anon_path.read_text(encoding="utf-8")),
        list(replacements.keys()),
    ):
        print(
            "error: anonymized output still contains PII tokens — extend _build_replacements before committing.",
            file=sys.stderr,
        )
        return 3

    print(f"wrote {raw_path} (gitignored) and {anon_path} (committable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
