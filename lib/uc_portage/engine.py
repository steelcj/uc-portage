"""The reconciler: plan, apply and harvest offerings into a target.

Ported from file-fairy 0.7.0 (file_fairy.py at commit 4416bcf). The sync
modes, managed blocks, retraction and the state file keep file-fairy's
semantics, recorded in decisions 0001 and 0002. What changed:

- items come from offerings rather than a manifest's groups;
- checksums normalise line endings, so a CRLF checkout is not an edit;
- two destinations differing only by case are refused;
- harvest reports target-side changes worth sending back;
- text is written with LF on every platform.

Sync modes, declared per offering (inherited) or per item (overrides):

    mirror          create if missing, overwrite when the source changed,
                    protect a local hand-edit (conflict, skipped unless
                    apply is run with --force)
    seed_if_missing create if the dest path is missing, otherwise leave
                    the target's copy alone regardless of content
    overwrite       the target never gets a vote; create or overwrite,
                    local edits included, no conflict state
    reference_only  declared but never touched

state: absent retracts a dest if it exists, whatever its history.

Managed blocks: a block item owns one marked region inside a file the
target otherwise owns, delimited by HTML comments:

    <!-- uc-portage:begin NAME -->
    ...the source file's content...
    <!-- uc-portage:end NAME -->

The region is reconciled per sync_mode with the region as the unit.
Missing markers mean the block is inserted at its anchor (EOF or BOF);
a missing dest is created holding only the block. Malformed markers are
an error, never a guess. Block state is tracked under "dest::NAME".

The state file, <target>/.uc-portage-state.yaml, records per dest the
source and dest checksums as of the last successful apply. That is what
tells "source changed upstream" apart from "target changed locally".
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List

import yaml

from .checksums import sha256_file, sha256_text
from .errors import PortageError
from .offerings import Item, Offering

STATE_FILENAME = ".uc-portage-state.yaml"
STATE_FORMAT = 1
MARKER_PREFIX = "uc-portage"

ACTIONABLE = ("new", "update")


# ── Managed block helpers ───────────────────────────────────────────────────

def block_markers(name: str) -> tuple:
    return (f"<!-- {MARKER_PREFIX}:begin {name} -->",
            f"<!-- {MARKER_PREFIX}:end {name} -->")


def split_block(text: str, name: str):
    """Return (before, body, after) around the named block's markers, or
    None if the markers are absent. Malformed markers are an error."""
    begin, end = block_markers(name)
    lines = text.splitlines(keepends=True)
    b_idx = [i for i, ln in enumerate(lines) if ln.strip() == begin]
    e_idx = [i for i, ln in enumerate(lines) if ln.strip() == end]
    if not b_idx and not e_idx:
        return None
    if len(b_idx) != 1 or len(e_idx) != 1 or e_idx[0] <= b_idx[0]:
        raise PortageError(f"malformed uc-portage block markers for "
                           f"{name!r}: expected exactly one begin and one "
                           f"end, begin before end")
    b, e = b_idx[0], e_idx[0]
    return ("".join(lines[: b + 1]),
            "".join(lines[b + 1: e]),
            "".join(lines[e:]))


def ensure_newline(text: str) -> str:
    return text if text.endswith("\n") or not text else text + "\n"


def read_text(path: Path) -> str:
    """Read text with universal newlines, so CRLF arrives as LF."""
    with path.open(encoding="utf-8") as f:
        return f.read()


def write_text(path: Path, text: str) -> None:
    """Write text with LF line endings on every platform."""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ── State ───────────────────────────────────────────────────────────────────

def state_path_for(target_root: Path) -> Path:
    return target_root / STATE_FILENAME


def load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        return {"format": STATE_FORMAT, "synced": {}}
    with state_path.open(encoding="utf-8") as f:
        state = yaml.safe_load(f) or {}
    if state.get("format", STATE_FORMAT) != STATE_FORMAT:
        raise PortageError(f"{state_path}: unsupported state format "
                           f"{state.get('format')!r}")
    state.setdefault("format", STATE_FORMAT)
    state.setdefault("synced", {})
    return state


def save_state(state_path: Path, state: dict) -> None:
    with state_path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(state, f, sort_keys=False)


# ── Destination checks ──────────────────────────────────────────────────────

def check_destinations(items: List[Item]) -> None:
    """Refuse destinations that cannot coexist in one checkout.

    Two dests differing only by case are one file on Windows and macOS
    and two on Linux, so they are refused everywhere. A dest may be
    claimed by one file or absent item, or by any number of blocks with
    distinct names, but not by both kinds and not twice.
    """
    by_fold: Dict[str, set] = {}
    claims: Dict[str, List[Item]] = {}
    for item in items:
        posix = PurePosixPath(item.dest)
        if posix.is_absolute() or ".." in posix.parts or "\\" in item.dest:
            raise PortageError(f"dest {item.dest!r} in offering "
                               f"{item.offering!r} must be a relative "
                               f"path inside the target")
        by_fold.setdefault(item.dest.casefold(), set()).add(item.dest)
        claims.setdefault(item.dest, []).append(item)

    for spellings in by_fold.values():
        if len(spellings) > 1:
            names = " and ".join(repr(s) for s in sorted(spellings))
            raise PortageError(f"case collision: {names} differ only by "
                               f"case and would be one file on Windows "
                               f"and macOS")

    for dest, claimants in claims.items():
        if len(claimants) == 1:
            continue
        blocks = [i for i in claimants if i.kind == "block"]
        names = [i.block for i in blocks]
        if len(blocks) != len(claimants) or len(set(names)) != len(names):
            owners = ", ".join(sorted({i.offering for i in claimants}))
            raise PortageError(f"dest {dest!r} is claimed more than once "
                               f"(by {owners})")


# ── Planning ────────────────────────────────────────────────────────────────

def build_plan(offerings: List[Offering], target_root: Path,
               state: dict) -> List[dict]:
    """Return one entry per item with a computed status: new, update,
    unchanged, present, conflict, missing-source, retract or retired.
    The status an item can reach depends on its sync mode; only mirror
    items can be in conflict."""
    items = [item for offering in offerings for item in offering.items]
    check_destinations(items)
    synced = state.get("synced", {})

    plan = []
    for item in items:
        dest_path = target_root / PurePosixPath(item.dest)
        entry = {
            "offering": item.offering,
            "source": item.source,
            "dest": item.dest,
            "source_path": item.source_path,
            "dest_path": dest_path,
            "mode": item.mode,
        }

        if item.kind == "absent":
            # Declared retraction: existence-keyed, blind to sync_mode
            # and to the state file (decision 0002, ruling 3).
            entry["status"] = "retract" if dest_path.is_file() else "retired"
            plan.append(entry)
            continue

        if item.kind == "block":
            plan.append(plan_block(item, entry, synced))
            continue

        if not item.source_path.is_file():
            entry["status"] = "missing-source"
            plan.append(entry)
            continue

        current_source_sha = sha256_file(item.source_path)
        entry["current_source_sha"] = current_source_sha
        dest_exists = dest_path.is_file()

        if item.mode == "seed_if_missing":
            # Existence-keyed, blind to the state file and to content:
            # plant it once when absent, then it is the target's own.
            entry["status"] = "present" if dest_exists else "new"
            plan.append(entry)
            continue

        if item.mode == "overwrite":
            # Content-keyed against the source alone; local edits are
            # not protected and there is no conflict state.
            if not dest_exists:
                entry["status"] = "new"
            elif sha256_file(dest_path) != current_source_sha:
                entry["status"] = "update"
            else:
                entry["status"] = "unchanged"
            plan.append(entry)
            continue

        # mirror, the default: three-way against the state record. First
        # contact with an existing, differing dest is a conflict, never a
        # clobber; an existing identical dest is adopted as new.
        record = synced.get(item.dest)
        if record is None:
            if dest_exists and sha256_file(dest_path) != current_source_sha:
                entry["status"] = "conflict"
            else:
                entry["status"] = "new"
        else:
            dest_drifted = (dest_exists and sha256_file(dest_path)
                            != record.get("dest_sha256"))
            source_changed = current_source_sha != record.get("source_sha256")
            if dest_drifted:
                entry["status"] = "conflict"
            elif not dest_exists:
                entry["status"] = "new"
            elif source_changed:
                entry["status"] = "update"
            else:
                entry["status"] = "unchanged"
        plan.append(entry)

    return plan


def plan_block(item: Item, entry: dict, synced: dict) -> dict:
    name = item.block
    entry["block"] = name
    entry["anchor"] = item.anchor
    entry["state_key"] = f"{item.dest}::{name}"
    if not item.source_path.is_file():
        entry["status"] = "missing-source"
        return entry
    desired = ensure_newline(read_text(item.source_path))
    entry["desired_body"] = desired
    entry["current_source_sha"] = sha256_text(desired)

    dest_path = entry["dest_path"]
    if not dest_path.is_file():
        entry["status"] = "new"
        return entry
    parts = split_block(read_text(dest_path), name)
    if parts is None:
        # Markers absent: insertion, the same for every mode.
        entry["status"] = "new"
        return entry
    body = parts[1]
    if item.mode == "seed_if_missing":
        entry["status"] = "present"
    elif body == desired:
        entry["status"] = "unchanged"
    elif item.mode == "overwrite":
        entry["status"] = "update"
    else:
        # mirror: three-way on the region through the state record. First
        # contact with a differing region is protected as a conflict.
        record = synced.get(entry["state_key"])
        if record is None or sha256_text(body) != record.get("dest_sha256"):
            entry["status"] = "conflict"
        else:
            entry["status"] = "update"
    return entry


# ── Applying ────────────────────────────────────────────────────────────────

def apply_block(entry: dict) -> None:
    """Write the desired body into dest: replace the region when the
    markers exist, insert at the anchor when they are absent, create the
    file when dest is absent. Text outside the markers is kept."""
    begin, end = block_markers(entry["block"])
    desired = entry["desired_body"]
    block_text = f"{begin}\n{desired}{end}\n"
    dest_path = entry["dest_path"]

    if not dest_path.is_file():
        write_text(dest_path, block_text)
        return

    text = read_text(dest_path)
    parts = split_block(text, entry["block"])
    if parts is not None:
        before, _, after = parts
        write_text(dest_path, before + desired + after)
    elif entry["anchor"] == "BOF":
        write_text(dest_path, block_text + "\n" + text)
    else:
        write_text(dest_path, ensure_newline(text) + "\n" + block_text)


def apply_plan(plan: List[dict], state: dict, state_path: Path,
               force: bool = False) -> List[tuple]:
    """Carry out new and update entries, conflicts too when forced, and
    retractions. Record each result in the state file. Return a list of
    (action, entry) pairs, where action is "synced" or "retracted"."""
    actionable = [e for e in plan if e["status"] in ACTIONABLE]
    if force:
        actionable += [e for e in plan if e["status"] == "conflict"]
    retractions = [e for e in plan if e["status"] == "retract"]

    synced = state.setdefault("synced", {})
    done = []
    for entry in actionable:
        dest_path = entry["dest_path"]
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = {
            "offering": entry["offering"],
            "source": entry["source"],
            "source_sha256": entry["current_source_sha"],
            "synced_at": stamp,
        }
        if "block" in entry:
            apply_block(entry)
            record["dest_sha256"] = sha256_text(entry["desired_body"])
            record["block"] = entry["block"]
            synced[entry["state_key"]] = record
        else:
            shutil.copyfile(entry["source_path"], dest_path)
            record["dest_sha256"] = sha256_file(dest_path)
            synced[entry["dest"]] = record
        done.append(("synced", entry))

    for entry in retractions:
        entry["dest_path"].unlink()
        synced.pop(entry["dest"], None)
        done.append(("retracted", entry))

    if done:
        save_state(state_path, state)
    return done


# ── Harvesting ──────────────────────────────────────────────────────────────

def build_harvest(plan: List[dict], state: dict) -> List[dict]:
    """Report items whose target changed since the last apply while their
    source did not: local improvements worth sending back upstream.

    A source-only change is ordinary upstream progress and is not
    reported; a change on both sides is a conflict, which plan reports.
    seed_if_missing items are skipped, because the target owns them by
    declaration. In 0.1.0 harvest only reports; it never writes.
    """
    synced = state.get("synced", {})
    found = []
    for entry in plan:
        if entry["mode"] == "seed_if_missing":
            continue
        if "current_source_sha" not in entry:
            continue          # absent items and missing sources
        key = entry.get("state_key", entry["dest"])
        record = synced.get(key)
        if record is None:
            continue          # never applied, so nothing to compare
        if entry["current_source_sha"] != record.get("source_sha256"):
            continue          # the source moved; not a target-only change
        dest_path = entry["dest_path"]
        change = None
        if "block" in entry:
            parts = (split_block(read_text(dest_path), entry["block"])
                     if dest_path.is_file() else None)
            if parts is None:
                change = "deleted"
            elif sha256_text(parts[1]) != record.get("dest_sha256"):
                change = "changed"
        elif not dest_path.is_file():
            change = "deleted"
        elif sha256_file(dest_path) != record.get("dest_sha256"):
            change = "changed"
        if change:
            found.append(dict(entry, change=change))
    return found
