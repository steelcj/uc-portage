"""uc-portage: a declarative file reconciler.

Compares what offerings say a repository should contain with what it
holds, plans the difference, applies it, and reports changes worth
sending back.
"""

from pathlib import Path


def _version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover, Python 3.8 has importlib.metadata
        return "unknown"
    try:
        return version("uc-portage")
    except PackageNotFoundError:
        # Running from a checkout that is not installed: VERSION is the
        # single source, as pyproject.toml reads it too.
        version_file = Path(__file__).resolve().parents[2] / "VERSION"
        if version_file.is_file():
            return version_file.read_text(encoding="utf-8").strip()
        return "unknown"


__version__ = _version()
