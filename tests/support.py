"""Shared scaffolding for the uc-portage tests.

Each test builds a scratch source directory of offerings and a scratch
target, runs the command in-process, and checks the result. Every
offering a test writes is checked against offering.schema.yaml: one
written as valid must validate, and one written as invalid must not, so
the schema and the engine never disagree unnoticed.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import yaml  # noqa: E402

from uc_portage import cli  # noqa: E402
from uc_portage.schema import offering_schema, validate  # noqa: E402


class Result:
    def __init__(self, code, out, err):
        self.returncode = code
        self.stdout = out
        self.stderr = err

    @property
    def output(self):
        return self.stdout + self.stderr


class PortageTestCase(unittest.TestCase):
    """A scratch workspace holding a source of offerings and a target."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    # ── Building offerings ──

    def offering(self, offering_id, items, valid=True, **fields):
        """Write source/<id>/offering.yaml and check its schema verdict."""
        data = {"format": 1, "id": offering_id}
        data.update(fields)
        data["items"] = items
        path = self.source / offering_id / "offering.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(yaml.safe_dump(data, sort_keys=False)
                         .encode("utf-8"))
        errors = validate(data, offering_schema())
        if valid:
            self.assertEqual(errors, [], f"{offering_id} should validate")
        else:
            self.assertNotEqual(errors, [],
                                f"{offering_id} should not validate")
        return path

    def source_file(self, offering_id, rel, text):
        path = self.source / offering_id / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def target_file(self, rel, text=None):
        path = self.target / rel
        if text is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        return path

    def read(self, rel):
        return (self.target / rel).read_bytes().decode("utf-8")

    # ── Running the command ──

    def run_cli(self, command, offerings, *extra):
        argv = [command, "--source", str(self.source),
                "--target", str(self.target)]
        for offering_id in offerings:
            argv += ["--offering", offering_id]
        argv += list(extra)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return Result(code, out.getvalue(), err.getvalue())

    def apply(self, *offerings, force=False):
        extra = ["--yes"] + (["--force"] if force else [])
        return self.run_cli("apply", offerings, *extra)

    def plan(self, *offerings):
        return self.run_cli("plan", offerings)

    def harvest(self, *offerings):
        return self.run_cli("harvest", offerings)
