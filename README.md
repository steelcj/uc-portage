# uc-portage

A declarative file reconciler. uc-portage compares what offerings say a repository should contain with what it holds, plans the difference, applies it, and reports changes worth sending back. A portage is the carry between two waters, in either direction, and the word is the same in French and English.

uc-portage succeeds the engine of [file-fairy](https://github.com/steelcj/file-fairy). It is generic: uc-automa uses it to deliver Vishpala's offerings, but uc-portage knows nothing of uc-automa.

## Requirements

Python 3.8 or later and PyYAML. uc-portage uses only the standard library otherwise, runs no shell commands and handles paths with `pathlib`, so it behaves the same on Linux, macOS and Windows.

## Install

From a checkout:

```sh
PYYAML_FORCE_LIBYAML=0 python3 -m pip install --no-binary pyyaml .
uc-portage --version
```

On Windows, in Command Prompt:

```bat
set PYYAML_FORCE_LIBYAML=0
python -m pip install --no-binary pyyaml .
```

### Why PyYAML is built as pure Python

uc-portage and uc-automa depend on PyYAML, whose optional C extension, built against libyaml, needs a C compiler wherever PyPI has no PyYAML wheel for your Python: PyYAML 6.0.3 has none for Python 3.15 on Windows. `--no-binary pyyaml` with `PYYAML_FORCE_LIBYAML=0` builds PyYAML from its source as pure Python on every platform instead, giving the same `py3-none-any` wheel everywhere, with no compiler.

The speed cost is none for uc-portage. They read and write YAML only through `yaml.safe_load` and `yaml.safe_dump`, which run PyYAML's Python code whether or not the extension is present; the extension speeds up only the `CLoader` and `CSafeLoader` family, which they do not use. Measured on 2026-10-11 on Linux with Python 3.12, loading all 19 YAML files uc-portage and uc-automa ship, 31 KB, took 41 ms with the pure build and 43 ms with PyYAML's binary wheel; `CSafeLoader` would have taken 5 ms. Another program in the same environment that imports `CSafeLoader` without a fallback fails with `ImportError`, so give the tools their own virtual environment if anything else there needs the extension.

## Use

```sh
uc-portage plan    --source DIR --offering ID[,ID...] [--target DIR] [--language TAG]
uc-portage status  ...            the same as plan
uc-portage apply   ... [--yes] [--force]
uc-portage harvest ...            report target-only changes; writes nothing
```

The guide, [Using uc-portage](en-ca/docs/guides/usage/using-uc-portage-v0.1.0.md), explains offerings, sync modes, managed blocks and each command. Offerings are checked against [`schemas/offering.schema.yaml`](schemas/offering.schema.yaml).

## Platform status

| Platform | Status |
| --- | --- |
| Linux | Tests pass, including wheel and editable installs, on Python 3.12 (Ubuntu 24.04) and Python 3.8 (AlmaLinux 8 container) |
| macOS | Not yet verified |
| Windows | Not yet marked verified: both criteria below passed on 2026-10-11, on Windows 11 with Python 3.15.0 from manage-python and PyYAML built as pure Python ([record](https://github.com/steelcj/osat-manager-restic/blob/main/tests/e2e/windows/2026-10-11--windows-test-run.md)). The network cut's self-test is to be repeated on a network with IPv6 first, as for osat-manager-restic |

Windows is verified when, on a clean Windows 11 snapshot, as an ordinary user who is not an administrator:

- the unit tests of uc-portage and uc-automa pass, with their install tests, and `uc-automa check` passes on uc-automa itself;
- uc-portage and uc-automa install with `pip install --no-index`, inside a network cut, from wheels built from their release tags and the pure `py3-none-any` PyYAML wheel, and the installed `uc-automa check` then passes on uc-automa at its tag.

`tests/e2e/windows/run_over_ssh.py` in osat-manager-restic runs both and writes a record.

## Develop

```sh
python3 -m unittest discover -s tests
```

The tests run from a checkout without installing; they build scratch offerings and targets and run the command in-process. Setting `UC_PORTAGE_INSTALL_TESTS=1` adds tests that build a wheel and an editable install in fresh virtual environments, which needs network access.

An editable install, `python3 -m pip install -e .`, needs pip 21.3 or later, because the project is defined by `pyproject.toml` alone.

`schemas/` lives once, at the repository root. `pyproject.toml` maps it into the package as `uc_portage.schemas`, so a wheel carries it. In an editable install or a checkout, `uc_portage.resources.data_dir` falls back to the repository root, but only after confirming that the root's `pyproject.toml` names this project; otherwise it fails with an error naming the missing data. The reasons are recorded in uc-automa 0019, *Decision: Package Data Mapped from the Repository Root* (`urn:uuid:7ba945fe-2f0d-45fb-a347-bda6d12294be`), which both tools follow.

## Documentation

| Path | What it holds |
| --- | --- |
| [`en-ca/docs/guides/usage/`](en-ca/docs/guides/usage/) | How to use uc-portage |
| [`en-ca/docs/decisions/`](en-ca/docs/decisions/) | The decisions that define its behaviour |

## License

uc-portage follows the REUSE convention: [`REUSE.toml`](REUSE.toml) records which licence covers which paths, and [`LICENSES/`](LICENSES/) holds their texts. Code is licensed under the MIT License, whose text is also in [`LICENSE`](LICENSE). Documentation is licensed under the Creative Commons Attribution 4.0 International License. Releases are MIT and CC BY 4.0 from 0.1.0, the first public release (uc-automa 0025).

This document, *uc-portage*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
