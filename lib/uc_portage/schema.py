"""A small JSON Schema validator, standard library only.

uc-portage's contracts are JSON Schema documents written in YAML, under
schemas/ at the repository root. Rather than depend on the jsonschema
package, this module implements the subset those schemas use, and
refuses any keyword outside it, so a schema can never silently ask for
a check that is not made.

Supported: $schema, $id, $defs, $ref (local, "#/$defs/NAME"), title,
description, type, const, enum, pattern, minLength, minItems, items,
properties, required, additionalProperties, oneOf.

uc-automa validates its own schemas with this module too, so the
subset is defined in one place.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .errors import PortageError
from .resources import data_dir

ANNOTATIONS = {"$schema", "$id", "$defs", "$comment", "title",
               "description"}
ASSERTIONS = {"$ref", "type", "const", "enum", "pattern", "minLength",
              "minItems", "items", "properties", "required",
              "additionalProperties", "oneOf"}

TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def schema_dir() -> Path:
    """The schemas/ directory, installed or in a checkout."""
    return data_dir("uc_portage", "uc-portage", "uc_portage.schemas",
                    "schemas")


def load_schema(name: str) -> dict:
    path = schema_dir() / name
    if not path.is_file():
        raise PortageError(f"schema not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def offering_schema() -> dict:
    return load_schema("offering.schema.yaml")


def validate(instance, schema: dict) -> list:
    """Return a list of error messages, empty when the instance is valid."""
    errors: list = []
    _check(instance, schema, schema, "$", errors)
    return errors


def _resolve(ref: str, root: dict) -> dict:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        raise PortageError(f"unsupported $ref {ref!r}; only {prefix}NAME")
    name = ref[len(prefix):]
    try:
        return root["$defs"][name]
    except KeyError:
        raise PortageError(f"$ref to undefined {ref!r}") from None


def _label(schema: dict, root: dict) -> str:
    if "$ref" in schema:
        target = _resolve(schema["$ref"], root)
        return target.get("title", schema["$ref"])
    return schema.get("title", "an alternative")


def _check(value, schema: dict, root: dict, where: str, errors: list) -> None:
    unknown = set(schema) - ANNOTATIONS - ASSERTIONS
    if unknown:
        raise PortageError(f"schema keyword(s) not supported by "
                           f"uc_portage.schema: {sorted(unknown)}")

    if "$ref" in schema:
        _check(value, _resolve(schema["$ref"], root), root, where, errors)

    if "type" in schema:
        wanted = schema["type"]
        names = wanted if isinstance(wanted, list) else [wanted]
        if not any(TYPES[n](value) for n in names):
            errors.append(f"{where}: expected {' or '.join(names)}, "
                          f"got {type(value).__name__}")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} is not one of "
                      f"{', '.join(map(str, schema['enum']))}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{where}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: {value!r} does not match "
                          f"{schema['pattern']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{where}: needs at least {schema['minItems']} "
                          f"item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                _check(item, schema["items"], root, f"{where}[{i}]", errors)

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing required key {key!r}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                _check(item, props[key], root, f"{where}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}: unexpected key {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _check(item, schema["additionalProperties"], root,
                       f"{where}.{key}", errors)

    if "oneOf" in schema:
        results = []
        for option in schema["oneOf"]:
            sub: list = []
            _check(value, option, root, where, sub)
            results.append((option, sub))
        matched = [opt for opt, sub in results if not sub]
        if len(matched) != 1:
            if not matched:
                detail = "; ".join(f"as {_label(opt, root)}: {sub[0]}"
                                   for opt, sub in results)
                errors.append(f"{where}: matches none of the allowed "
                              f"shapes ({detail})")
            else:
                names = ", ".join(_label(opt, root) for opt in matched)
                errors.append(f"{where}: matches more than one shape "
                              f"({names})")
