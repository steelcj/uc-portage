"""Finding a package's data directories, installed or in a checkout.

Data such as schemas/ lives once, at the repository root, and
pyproject.toml maps it into the package (for example uc_portage.schemas
from schemas/), so a built wheel carries it. An editable install cannot
resolve such a mapping without an __init__.py in the data directory, and
a checkout run without installing has no mapping at all. For those two
cases the resolver falls back to the repository root, but only after
proving it is in that package's checkout: the root must hold a
pyproject.toml whose project name matches. Anything else is an error
naming the missing data; data is never read from an unexpected place.

The fallback relies on the package sitting at lib/<package>/, two levels
below the repository root, as decision D4 fixes. Changing D4 means
changing this resolver.

This is the one resolver: uc-automa imports it rather than keeping a
copy.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
from pathlib import Path

from .errors import PortageError

PROJECT_TABLE = re.compile(r"^\[project\]\s*$")
ANY_TABLE = re.compile(r"^\[")
NAME_KEY = re.compile(r"""^name\s*=\s*["']([^"']+)["']\s*$""")


def normalise_name(name: str) -> str:
    """Compare project names as packaging does (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def project_name(pyproject: Path):
    """The [project] name in a pyproject.toml, or None.

    Python 3.8 has no TOML parser in the standard library, so this reads
    only the one key it needs: a quoted name directly in [project].
    """
    in_project = False
    with pyproject.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if PROJECT_TABLE.match(line):
                in_project = True
            elif ANY_TABLE.match(line):
                in_project = False
            elif in_project:
                match = NAME_KEY.match(line)
                if match:
                    return match.group(1)
    return None


def checkout_root(package: str, project: str) -> Path:
    """The repository root of the checkout the package was imported
    from, after proving it is that project's checkout."""
    module = importlib.import_module(package)
    package_dir = Path(module.__file__).resolve().parent
    root = package_dir.parents[1]          # lib/<package>/ (D4)
    pyproject = root / "pyproject.toml"
    if package_dir != root / "lib" / package:
        raise PortageError(f"{package} is not at lib/{package}/ under a "
                           f"repository root ({package_dir})")
    if not pyproject.is_file():
        raise PortageError(f"no pyproject.toml at {root}, so it is not a "
                           f"{project} checkout")
    found = project_name(pyproject)
    if found is None or normalise_name(found) != normalise_name(project):
        raise PortageError(f"{pyproject} names project {found!r}, not "
                           f"{project!r}")
    return root


def data_dir(package: str, project: str, subpackage: str,
             repo_path: str) -> Path:
    """Return the directory holding a package's mapped data.

    package     the import name, such as "uc_portage"
    project     the project name in pyproject.toml, such as "uc-portage"
    subpackage  the name the data is mapped to, such as "uc_portage.schemas"
    repo_path   where the data lives in the repository, such as "schemas"
                or "en-ca/conf", always with forward slashes
    """
    try:
        spec = importlib.util.find_spec(subpackage)
    except ModuleNotFoundError:
        spec = None
    if spec is not None and spec.submodule_search_locations:
        for location in spec.submodule_search_locations:
            if Path(location).is_dir():
                return Path(location)

    try:
        root = checkout_root(package, project)
    except PortageError as exc:
        raise PortageError(
            f"cannot find {project}'s data {repo_path!r}: it is not "
            f"installed as {subpackage}, and the fallback to a checkout "
            f"failed: {exc}") from None
    location = root.joinpath(*repo_path.split("/"))
    if not location.is_dir():
        raise PortageError(f"cannot find {project}'s data {repo_path!r}: "
                           f"{location} does not exist in the checkout")
    return location
