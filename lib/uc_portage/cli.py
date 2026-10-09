"""The uc-portage command.

    uc-portage plan    --source DIR --offering ID [...] [--target DIR]
    uc-portage status  (the same as plan)
    uc-portage apply   ... [--yes] [--force]
    uc-portage harvest ...

--source is a directory holding offerings side by side, one directory
per offering, each with its offering.yaml. --offering names a subscribed
offering and may be repeated or given a comma-separated list. --target
is the receiving repository, the current directory by default.
--language fills {language} in source paths.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .engine import (apply_plan, build_harvest, build_plan, load_state,
                     state_path_for)
from .errors import PortageError
from .offerings import load_offerings

ORDER = ["retract", "conflict", "missing-source", "new", "update",
         "present", "retired", "unchanged"]
LABELS = {
    "retract": "RETRACT  (declared absent; will be deleted)",
    "conflict": "CONFLICT  (target changed locally since last sync)",
    "missing-source": "MISSING SOURCE  (file does not exist in the offering)",
    "new": "NEW  (not yet synced)",
    "update": "UPDATE  (source changed since last sync)",
    "present": "present  (seed_if_missing; the target owns it)",
    "retired": "retired  (declared absent; already gone)",
    "unchanged": "unchanged",
}


def log(message: str) -> None:
    print(f"[uc-portage] {message}")


def describe(entry: dict) -> str:
    if entry["status"] in ("retract", "retired"):
        return f"  [{entry['offering']}] {entry['dest']}"
    if "block" in entry:
        return (f"  [{entry['offering']}] {entry['source']} -> "
                f"{entry['dest']} (block {entry['block']})")
    return f"  [{entry['offering']}] {entry['source']} -> {entry['dest']}"


def print_plan(plan: List[dict]) -> None:
    if not plan:
        log("nothing to do: the subscribed offerings deliver no items")
        return
    by_status: dict = {}
    for entry in plan:
        by_status.setdefault(entry["status"], []).append(entry)
    for status in ORDER:
        entries = by_status.get(status)
        if not entries:
            continue
        print(f"\n{LABELS[status]}")
        for entry in entries:
            print(describe(entry))

    def count(status):
        return len(by_status.get(status, []))

    print()
    log(f"{count('new') + count('update')} item(s) would be synced, "
        f"{count('retract')} retraction(s), {count('conflict')} "
        f"conflict(s), {count('missing-source')} missing source(s)")


def parse_ids(values: List[str]) -> List[str]:
    ids = []
    for value in values:
        ids.extend(part.strip() for part in value.split(",") if part.strip())
    return ids


def load(args: argparse.Namespace):
    target_root = Path(args.target).expanduser()
    if not target_root.is_dir():
        raise PortageError(f"target not found: {target_root}")
    offerings = load_offerings(Path(args.source).expanduser(),
                               parse_ids(args.offering), args.language)
    state_path = state_path_for(target_root)
    state = load_state(state_path)
    return build_plan(offerings, target_root, state), state, state_path


def cmd_plan(args: argparse.Namespace) -> int:
    plan, _, _ = load(args)
    print_plan(plan)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    plan, state, state_path = load(args)
    conflicts = [e for e in plan if e["status"] == "conflict"]
    missing = [e for e in plan if e["status"] == "missing-source"]
    to_do = [e for e in plan if e["status"] in ("new", "update", "retract")]

    if missing:
        log(f"{len(missing)} item(s) have no source file; skipping them:")
        for entry in missing:
            print(f"  [{entry['offering']}] {entry['source']} (not found)")

    if conflicts and not args.force:
        log(f"{len(conflicts)} mirror item(s) are in conflict and will be "
            f"skipped (target changed locally since last sync). Resolve "
            f"by hand, or overwrite just this once with --force; if the "
            f"target should never keep local edits, declare "
            f"sync_mode: overwrite in the offering instead:")
        for entry in conflicts:
            print(f"  [{entry['offering']}] {entry['dest']}")
    if args.force:
        to_do += conflicts

    if not to_do:
        log("nothing to apply")
        return 0

    if not args.yes:
        print()
        print_plan(to_do)
        answer = input("\nApply the above? [y/N] ").strip().lower()
        if answer != "y":
            log("aborted, nothing written")
            return 1

    done = apply_plan(plan, state, state_path, force=args.force)
    for action, entry in done:
        if action == "retracted":
            print(f"  retracted: {entry['dest']}")
        elif "block" in entry:
            print(f"  synced: {entry['source']} -> {entry['dest']} "
                  f"(block {entry['block']})")
        else:
            print(f"  synced: {entry['source']} -> {entry['dest']}")
    synced = sum(1 for action, _ in done if action == "synced")
    log(f"{synced} item(s) synced, {len(done) - synced} retracted; "
        f"state written to {state_path}")
    return 0


def cmd_harvest(args: argparse.Namespace) -> int:
    plan, state, _ = load(args)
    found = build_harvest(plan, state)
    if not found:
        log("nothing to harvest: no target-only changes")
        return 0
    print("\nHARVEST  (target changed, source did not; worth sending back)")
    for entry in found:
        suffix = f" (block {entry['block']})" if "block" in entry else ""
        print(f"  [{entry['offering']}] {entry['dest']}{suffix}: "
              f"{entry['change']}")
    print()
    log(f"{len(found)} target-only change(s); harvest reports only, "
        f"nothing was written")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uc-portage",
        description="Declarative file reconciler: carry offerings into a "
                    "repository with plan, apply, status and harvest.")
    parser.add_argument("--version", action="version",
                        version=f"uc-portage {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--source", required=True, metavar="DIR",
                        help="Directory holding the offerings, one "
                             "subdirectory each.")
    common.add_argument("--offering", required=True, action="append",
                        metavar="ID",
                        help="A subscribed offering; repeat, or give a "
                             "comma-separated list.")
    common.add_argument("--target", default=".", metavar="DIR",
                        help="The receiving repository (default: the "
                             "current directory).")
    common.add_argument("--language", metavar="TAG",
                        help="Language for {language} in source paths, "
                             "such as en-ca.")

    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", parents=[common],
                       help="Show what would change; no writes.")
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("status", parents=[common], help="The same as plan.")
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("apply", parents=[common],
                       help="Carry new and updated items into the target.")
    p.add_argument("--yes", action="store_true",
                   help="Skip the confirmation prompt.")
    p.add_argument("--force", action="store_true",
                   help="One-off override for mirror items in conflict: "
                        "overwrite them this run. The standing form is "
                        "sync_mode: overwrite in the offering.")
    p.set_defaults(func=cmd_apply)
    p = sub.add_parser("harvest", parents=[common],
                       help="Report target-only changes worth sending "
                            "back; writes nothing.")
    p.set_defaults(func=cmd_harvest)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PortageError as exc:
        print(f"[uc-portage ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
