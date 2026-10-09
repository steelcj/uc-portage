# Contributing

Changes arrive as commits on a branch, reviewed by Christopher Steel before they reach `main`.

## Before committing

- Run `python3 -m unittest discover -s tests`; every test passes.
- A change to behaviour comes with a test that fails without it.
- A change to the offering format changes `schemas/offering.schema.yaml` and the guide in the same commit.
- A file's licence follows its category, as [`REUSE.toml`](REUSE.toml) records: code GPL-3.0-or-later, documentation CC-BY-SA-4.0.

## Documents

Documents carry Dublin Core and `sat:` front matter, a Changelog table and a License section. Before 1.0.0 a document's filename carries its version with dots, as in `-v0.1.0`; a bump renames the file with `git mv` and updates its links in the same commit.

## License

This document, *Contributing*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
