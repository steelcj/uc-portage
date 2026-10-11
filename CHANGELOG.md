# Changelog

All notable changes to uc-portage are recorded here, in the form of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). uc-portage follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Decision 0004, guarded retraction, to be implemented in 0.2.0.
- The README states what verifies Windows: the unit tests, and an install from wheels with `pip install --no-index` inside a network cut.

### Changed

- The README's Windows status records the Windows run of 2026-10-11, which met both criteria; Windows is not yet marked verified, pending the network cut's self-test on a network with IPv6.
- The README installs PyYAML as pure Python, with `--no-binary pyyaml` and `PYYAML_FORCE_LIBYAML=0`, so no platform needs a C compiler, and records that this costs uc-portage no speed.

## [0.1.0] - 2026-10-11

### Added

- The reconciliation engine from file-fairy 0.7.0, with its tests: the `mirror`, `seed_if_missing`, `overwrite` and `reference_only` sync modes, managed blocks, `state: absent` retraction, and the per-target state file with checksums.
- Offerings as the front end: `offering.yaml` files, loaded by identifier from a source directory, in place of file-fairy's manifests with local source and target paths.
- `schemas/offering.schema.yaml`, and a standard-library validator for the subset of JSON Schema it uses.
- `uc_portage.resources.data_dir`, the one resolver for package data mapped in from the repository root, shared with uc-automa: installed packages read their own copy; editable installs and checkouts fall back to the repository root only after proving it is this project's checkout.
- Checksums that normalise line endings in text files, so a CRLF checkout is not reported as a local edit; text is written with LF.
- A case-collision check, and a check that no dest is claimed twice or lies outside the target, nor any source outside its offering (decision 0003).
- `{language}` in source paths, filled with the subscribing repository's language, given as `--language`, and falling back to the offering's `source_language` only when that translation is missing.
- `uc-portage plan`, `status`, `apply` and `harvest`; `harvest` reports target-only changes and writes nothing.
- Decision records migrated from file-fairy, the declared sync policy and one key per axis, and decision 0003, destinations stay inside the target.

- Subscribed to uc-automa with `layout: python-tool`: `.uc-automa.yaml`, the `.uc-portage.assets/` sidecar, the offerings' signpost block in `CLAUDE.md`, and a generated `en-ca/docs/README.md`.

### Changed from file-fairy

- The command is `uc-portage`; there is no short alias and no bare form that means apply.
- The state file is `.uc-portage-state.yaml`, and block markers read `uc-portage:begin` and `uc-portage:end`.
- Items with no source, which file-fairy kept as notes, are not part of the offering format.
- Code is licensed MIT and documentation CC BY 4.0, replacing file-fairy's AGPL-3.0-or-later (uc-automa 0025).
