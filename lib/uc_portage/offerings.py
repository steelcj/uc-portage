"""Reading offerings: the front end that replaces file-fairy's manifests.

An offering is a directory holding an offering.yaml and the files it
delivers. A receiving repository names the offerings it subscribes to;
uc-portage loads each one from a source directory that holds offerings
side by side, checks it against schemas/offering.schema.yaml, and turns
its items into Item records the engine plans with.

Where file-fairy had groups, uc-portage has offerings: an offering's
sync_mode is the default its items inherit, as a group's was.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import List, Optional

import yaml

from .errors import PortageError
from .schema import offering_schema, validate

OFFERING_FILENAME = "offering.yaml"

SYNC_MODES = ("mirror", "seed_if_missing", "overwrite", "reference_only")
STATES = ("file", "absent")
SCHEDULED_STATES = ("directory", "touch")
SCHEDULED_KEYS = ("content", "substitute", "glob", "exclude")
ANCHORS = ("EOF", "BOF")
LANGUAGE_PLACEHOLDER = "{language}"


@dataclass
class Item:
    """One thing an offering delivers or retracts, ready to plan."""

    offering: str
    kind: str                    # "file", "block" or "absent"
    dest: str
    mode: str
    source: Optional[str] = None          # as declared, for messages
    source_path: Optional[Path] = None    # resolved on disk
    block: Optional[str] = None
    anchor: str = "EOF"


@dataclass
class Offering:
    id: str
    path: Path
    data: dict
    items: List[Item]


def read_offering_file(path: Path) -> dict:
    if not path.is_file():
        raise PortageError(f"offering not found: {path}")
    with path.open(encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise PortageError(f"{path}: not valid YAML: {exc}") from None
    if not isinstance(data, dict):
        raise PortageError(f"{path}: an offering is a mapping")
    return data


def refuse_unimplemented(data: dict, offering_id: str) -> None:
    """Name the keys and values that are scheduled or unknown before the
    schema sees them, so the message says why, not only that it failed."""
    def check_mode(mode, where):
        if mode is not None and mode not in SYNC_MODES:
            raise PortageError(
                f"unknown sync_mode {mode!r} in {where}; "
                f"valid modes: {', '.join(SYNC_MODES)}")

    check_mode(data.get("sync_mode"), f"offering {offering_id!r}")
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        where = f"offering {offering_id!r}"
        for key in SCHEDULED_KEYS:
            if key in item:
                raise PortageError(
                    f"{key!r} in {where} is scheduled but not yet "
                    f"implemented (see decision 0002's implementation "
                    f"order)")
        check_mode(item.get("sync_mode"), where)
        state = item.get("state", "file")
        if state in SCHEDULED_STATES:
            raise PortageError(
                f"state {state!r} in {where} is scheduled but not yet "
                f"implemented (see decision 0002's implementation order)")
        if state not in STATES:
            raise PortageError(f"unknown state {state!r} in {where}; "
                               f"valid states: {', '.join(STATES)}")
        if "block" in item and "state" in item:
            raise PortageError(f"block item {item['block']!r} in {where} "
                               f"cannot combine with state")
        if "block" in item and item.get("anchor", "EOF") not in ANCHORS:
            raise PortageError(
                f"unsupported anchor {item.get('anchor')!r} for block "
                f"{item['block']!r}; valid: {', '.join(ANCHORS)}")


def check_offering(data: dict, offering_id: str, path: Path) -> None:
    refuse_unimplemented(data, offering_id)
    errors = validate(data, offering_schema())
    if errors:
        raise PortageError(f"{path} does not match offering.schema.yaml:\n  "
                           + "\n  ".join(errors))
    if data["id"] != offering_id:
        raise PortageError(f"{path}: id {data['id']!r} does not match its "
                           f"directory name {offering_id!r}")


def resolve_source(offering_dir: Path, source: str, language: Optional[str],
                   source_language: Optional[str], offering_id: str) -> Path:
    """Resolve a source path, filling {language} with the subscriber's
    language and falling back to the offering's source language when the
    subscriber's language has no file of its own."""
    if LANGUAGE_PLACEHOLDER not in source:
        return offering_dir / PurePosixPath(source)
    candidates = [lang for lang in (language, source_language) if lang]
    if not candidates:
        raise PortageError(
            f"offering {offering_id!r} uses {LANGUAGE_PLACEHOLDER} in "
            f"{source!r} but neither a language nor the offering's "
            f"source_language is given")
    for lang in candidates:
        path = offering_dir / PurePosixPath(
            source.replace(LANGUAGE_PLACEHOLDER, lang))
        if path.is_file():
            return path
    # Neither exists: report the first candidate as the missing source.
    return offering_dir / PurePosixPath(
        source.replace(LANGUAGE_PLACEHOLDER, candidates[0]))


def load_offering(source_root: Path, offering_id: str,
                  language: Optional[str] = None) -> Offering:
    offering_dir = source_root / offering_id
    path = offering_dir / OFFERING_FILENAME
    data = read_offering_file(path)
    check_offering(data, offering_id, path)

    default_mode = data.get("sync_mode", "mirror")
    source_language = data.get("source_language")
    items: List[Item] = []
    for raw in data["items"]:
        mode = raw.get("sync_mode", default_mode)
        if mode == "reference_only":
            continue
        if raw.get("state") == "absent":
            items.append(Item(offering_id, "absent", raw["dest"], mode))
            continue
        source_path = resolve_source(offering_dir, raw["source"], language,
                                     source_language, offering_id)
        if "block" in raw:
            items.append(Item(offering_id, "block", raw["dest"], mode,
                              raw["source"], source_path, raw["block"],
                              raw.get("anchor", "EOF")))
        else:
            items.append(Item(offering_id, "file", raw["dest"], mode,
                              raw["source"], source_path))
    return Offering(offering_id, offering_dir, data, items)


def load_offerings(source_root: Path, offering_ids: List[str],
                   language: Optional[str] = None) -> List[Offering]:
    if not source_root.is_dir():
        raise PortageError(f"offering source not found: {source_root}")
    seen = set()
    offerings = []
    for offering_id in offering_ids:
        if offering_id in seen:
            raise PortageError(f"offering {offering_id!r} is subscribed "
                               f"twice")
        seen.add(offering_id)
        offerings.append(load_offering(source_root, offering_id, language))
    return offerings
