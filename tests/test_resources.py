"""The data resolver: installed, editable and checkout cases.

The checkout cases run everywhere and offline. The wheel and editable
cases build fresh virtual environments and install PyYAML into them, so
they need network access and take a minute; they run when
UC_PORTAGE_INSTALL_TESTS=1 is set.
"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path

import support  # noqa: F401  (puts lib/ on sys.path)

from uc_portage.errors import PortageError
from uc_portage.resources import data_dir, project_name

REPO = Path(__file__).resolve().parents[1]
PROBE = ("from uc_portage.schema import schema_dir, offering_schema; "
         "offering_schema(); print(schema_dir())")


class FakeCheckout(unittest.TestCase):
    """A throwaway package laid out as lib/<package>/ under a root."""

    count = 0

    def setUp(self):
        FakeCheckout.count += 1
        self.package = f"fakepkg{FakeCheckout.count}"
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        package_dir = self.root / "lib" / self.package
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "data").mkdir()
        sys.path.insert(0, str(self.root / "lib"))

    def tearDown(self):
        sys.path.remove(str(self.root / "lib"))
        sys.modules.pop(self.package, None)
        importlib.invalidate_caches()
        self._tmp.cleanup()

    def pyproject(self, name):
        (self.root / "pyproject.toml").write_text(
            f'[build-system]\nrequires = ["setuptools"]\n\n'
            f'[project]\nname = "{name}"\n', encoding="utf-8")

    def resolve(self, repo_path="data", project="fake-pkg"):
        return data_dir(self.package, project, f"{self.package}.data",
                        repo_path)

    def test_a_proven_checkout_resolves_to_the_repository_root(self):
        self.pyproject("fake_pkg")      # names compare as packaging does
        self.assertEqual(self.resolve(), self.root / "data")

    def test_without_pyproject_it_fails_and_names_the_data(self):
        with self.assertRaises(PortageError) as caught:
            self.resolve()
        self.assertIn("'data'", str(caught.exception))
        self.assertIn("no pyproject.toml", str(caught.exception))

    def test_another_projects_checkout_is_refused(self):
        self.pyproject("someone-else")
        with self.assertRaises(PortageError) as caught:
            self.resolve()
        self.assertIn("someone-else", str(caught.exception))

    def test_missing_data_in_a_proven_checkout_is_an_error(self):
        self.pyproject("fake-pkg")
        with self.assertRaises(PortageError) as caught:
            self.resolve("en-ca/conf")
        self.assertIn("does not exist", str(caught.exception))

    def test_project_name_reads_only_the_project_table(self):
        (self.root / "pyproject.toml").write_text(
            '[tool.other]\nname = "decoy"\n\n[project]\n'
            'description = "x"\nname = "real"\n', encoding="utf-8")
        self.assertEqual(project_name(self.root / "pyproject.toml"), "real")


def bin_dir(env: Path) -> Path:
    return env / ("Scripts" if os.name == "nt" else "bin")


def python_in(env: Path) -> Path:
    return bin_dir(env) / ("python.exe" if os.name == "nt" else "python")


class Checkout(unittest.TestCase):

    def test_running_from_the_checkout_reads_its_schemas(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            env = dict(os.environ, PYTHONPATH=str(REPO / "lib"))
            r = subprocess.run([sys.executable, "-c", PROBE], cwd=elsewhere,
                               env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(r.stdout.strip()), REPO / "schemas")


@unittest.skipUnless(os.environ.get("UC_PORTAGE_INSTALL_TESTS") == "1",
                     "set UC_PORTAGE_INSTALL_TESTS=1 to build and install "
                     "into fresh virtual environments (needs network)")
class Installs(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Install from a copy, so builds leave nothing in the checkout.
        self.src = self.tmp / "src"
        shutil.copytree(REPO, self.src, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "build", "dist", "*.egg-info", ".venv*"))

    def tearDown(self):
        self._tmp.cleanup()

    def fresh_env(self, name):
        env = self.tmp / name
        # Symbolic links on POSIX, as `python -m venv` makes them: a copied
        # interpreter cannot find its libpython in builds that link it
        # relative to the binary, such as python-build-standalone's 3.8.
        venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(env)
        # Editable installs without setup.py need pip 21.3 or later
        # (PEP 660); some Python 3.8 builds bundle an older pip.
        self.run_in(env, "-m", "pip", "install", "-q", "--upgrade", "pip")
        return env

    def run_in(self, env, *args, cwd=None):
        r = subprocess.run([str(python_in(env)), *args], cwd=cwd or self.tmp,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def probe(self, env):
        return Path(self.run_in(env, "-c", PROBE).strip())

    def test_wheel_in_a_fresh_environment(self):
        builder = self.fresh_env("builder")
        wheels = self.tmp / "wheels"
        self.run_in(builder, "-m", "pip", "wheel", "--no-deps", "-q",
                    "-w", str(wheels), str(self.src))
        wheel = next(wheels.glob("uc_portage-*.whl"))
        env = self.fresh_env("wheel")
        self.run_in(env, "-m", "pip", "install", "-q", str(wheel))
        found = self.probe(env)
        self.assertEqual(found.name, "schemas")
        self.assertEqual(found.parent.name, "uc_portage")
        self.assertNotIn(self.src, found.parents)
        self.assertTrue(
            str(found.resolve()).startswith(str(env.resolve())),
            "an installed wheel reads its own copy of the schemas")

        # Without its data, an installed wheel fails clearly rather than
        # reading from anywhere else.
        shutil.rmtree(found)
        r = subprocess.run([str(python_in(env)), "-c", PROBE], cwd=self.tmp,
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot find uc-portage's data 'schemas'", r.stderr)

    def test_editable_install(self):
        env = self.fresh_env("editable")
        self.run_in(env, "-m", "pip", "install", "-q", "-e", str(self.src))
        self.assertEqual(self.probe(env).resolve(),
                         (self.src / "schemas").resolve())


if __name__ == "__main__":
    unittest.main()
