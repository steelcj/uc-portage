# uc-portage

A declarative file reconciler. uc-portage compares what offerings say a repository should contain with what it holds, plans the difference, applies it, and reports changes worth sending back. A portage is the carry between two waters, in either direction, and the word is the same in French and English.

uc-portage succeeds the engine of [file-fairy](https://github.com/steelcj/file-fairy). It is generic: uc-automa uses it to deliver Vishpala's offerings, but uc-portage knows nothing of uc-automa.

## Requirements

Python 3.8 or later and PyYAML. uc-portage uses only the standard library otherwise, runs no shell commands and handles paths with `pathlib`, so it behaves the same on Linux, macOS and Windows.

## Install

```sh
python3 -m pip install .
uc-portage --version
```

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
| Windows | Not yet verified |

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

uc-portage follows the REUSE convention: [`REUSE.toml`](REUSE.toml) records which licence covers which paths, and [`LICENSES/`](LICENSES/) holds their texts. Code is licensed under the GNU General Public License v3.0 or later, whose text is also in [`LICENSE`](LICENSE). Documentation is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License.

This document, *uc-portage*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
