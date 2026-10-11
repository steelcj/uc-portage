---
title: "Using uc-portage"
dc:title: "Using uc-portage"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "uc-portage, offerings, offering.yaml, plan, apply, status, harvest, sync modes, managed blocks"
dc:description: "How to write an offering, subscribe a repository to offerings, and use uc-portage's plan, apply, status and harvest commands."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:082a3b92-9f80-4162-a767-a010c2650644"
dc:language: "en-CA"
dc:rights: "CC-BY-4.0"
sat:version: "0.1.0"
sat:status: "Accepted"
---

# Using uc-portage

Version: 0.1.0
Status: Accepted

## Summary

uc-portage keeps shared files in step across repositories. A publishing repository holds offerings, each a directory with an `offering.yaml` and the files it delivers. A receiving repository subscribes to some of them. uc-portage compares what the offerings say the receiving repository should hold with what it does hold, plans the difference, applies it, and reports local changes worth sending back. A portage is the carry between two waters, in either direction.

uc-portage is generic. uc-automa uses it to deliver Vishpala's offerings, reading each repository's subscriptions from `.uc-automa.yaml` and handing them to uc-portage, but uc-portage itself knows nothing of uc-automa.

## Install

uc-portage needs Python 3.8 or later and PyYAML. From a checkout:

```sh
python3 -m pip install .
uc-portage --version
```

## Offerings

An offering lives in its own directory, named by its identifier, beside the other offerings in a source directory:

```text
offerings/
├── editorconfig/
│   ├── offering.yaml
│   └── files/
│       └── .editorconfig
└── licence-block/
    ├── offering.yaml
    ├── en-ca/
    │   └── block.md
    └── fr-ca/
        └── block.md
```

`offering.yaml` names what the offering delivers. Source paths are relative to the offering's directory; dest paths are relative to the receiving repository's root and always use forward slashes.

```yaml
format: 1
id: "editorconfig"
title: "Editor defaults"
sync_mode: overwrite
items:
  - source: "files/.editorconfig"
    dest: ".editorconfig"
```

Every `offering.yaml` must match `schemas/offering.schema.yaml`, and its `id` must match its directory name. uc-portage checks both before planning.

### Items

An item has one of three shapes.

| Shape | Keys | What it does |
| --- | --- | --- |
| File | `source`, `dest`, optional `sync_mode` | Delivers a whole file |
| Block | `block`, `source`, `dest`, optional `anchor` and `sync_mode` | Owns one marked region inside a file the target otherwise owns |
| Absent | `state: absent`, `dest` | Deletes the dest if it exists |

A block's region sits between two HTML comments, which are invisible when Markdown is rendered:

```markdown
<!-- uc-portage:begin licence -->
...the source file's content...
<!-- uc-portage:end licence -->
```

When the markers are missing, the block is inserted at its `anchor`, `EOF` by default or `BOF`. When the dest is missing, it is created holding only the block. Everything outside the markers belongs to the receiving repository and is never touched. Markers that are duplicated or out of order are an error.

### Sync modes

`sync_mode` on the offering is the default for its items, and an item's own `sync_mode` overrides it. Without either, an item is `mirror`.

| `sync_mode` | Dest missing | Dest present, source changed | Dest present, locally edited |
| --- | --- | --- | --- |
| `mirror` | create | overwrite | protect (conflict, skip) |
| `seed_if_missing` | create | do nothing | do nothing |
| `overwrite` | create | overwrite | overwrite |
| `reference_only` | never touch | never touch | never touch |

`mirror` treats first contact with an existing, differing file or region as a conflict, never overwriting it, and adopts an identical one. The reasons for these modes are in the declared sync policy <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a), and the item shapes in one key per axis <a id="cite-steel-2026b"></a>[(Steel, 2026b)](#ref-steel-2026b).

### Languages

A source path may contain `{language}`. uc-portage fills it with the subscribing repository's language, given as `--language`, so a `fr-ca` repository receives the French text. Only when the offering has no file in that language does uc-portage fall back to the offering's `source_language`. uc-portage takes the language as a parameter and reads no configuration of its own; uc-automa passes the language from the repository's `.uc-automa.yaml`.

```yaml
format: 1
id: "licence-block"
source_language: "en-ca"
items:
  - block: "licence"
    source: "{language}/block.md"
    dest: "README.md"
```

## Commands

Every command takes the same options.

| Option | Meaning |
| --- | --- |
| `--source DIR` | The directory holding the offerings |
| `--offering ID` | A subscribed offering; repeat it, or give a comma-separated list |
| `--target DIR` | The receiving repository; the current directory by default |
| `--language TAG` | The language for `{language}` in source paths, such as `en-ca` |

### Plan and status

`uc-portage plan` shows what would change and writes nothing. `uc-portage status` is the same command under a name that reads better when nothing is about to change.

```sh
uc-portage plan --source ../uc-automa/offerings --offering editorconfig,line-endings
```

Each item is reported in one of these states:

| State | Meaning |
| --- | --- |
| `RETRACT` | Declared absent and present; apply deletes it |
| `CONFLICT` | A `mirror` item changed locally since it was last delivered |
| `MISSING SOURCE` | The offering names a file it does not hold |
| `NEW` | Not yet delivered |
| `UPDATE` | The source changed since it was last delivered |
| `present` | A `seed_if_missing` item the target now owns |
| `retired` | Declared absent and already gone |
| `unchanged` | Nothing to do |

### Apply

`uc-portage apply` shows the plan, asks for confirmation and carries out new items, updates and retractions. `--yes` skips the question. Conflicts are skipped and listed; `--force` overwrites them for this run only. If a file should never keep local edits, declare `sync_mode: overwrite` in the offering rather than reaching for `--force` each time.

```sh
uc-portage apply --source ../uc-automa/offerings --offering editorconfig --yes
```

Apply records what it delivered in `.uc-portage-state.yaml` at the target's root: for each dest, the checksums of the source and the dest as delivered. That record is how a later plan tells an upstream change from a local edit, so commit it with the files it describes.

### Harvest

`uc-portage harvest` reports files and blocks whose target changed since they were delivered while their source did not. Those are local improvements that may be worth sending back to the offering. A change only at the source is ordinary upstream progress and is not reported; a change on both sides is a conflict, which `plan` reports. `seed_if_missing` items are skipped, because the target owns them.

In 0.1.0 harvest only reports. Writing changes back to the publishing repository is planned for 0.2.0.

## Behaviour on every platform

- Checksums ignore line endings in text files, so a checkout with CRLF line endings, as git can produce on Windows, is not reported as edited. A file is text when it holds no NUL byte.
- Text uc-portage writes, such as files holding blocks, is written with LF line endings.
- Two dests that differ only by case, such as `README.md` and `readme.md`, are refused, because they are one file on Windows and macOS and two on Linux.
- A dest is claimed by one file or absent item, or by any number of blocks with distinct names, never twice.
- A dest must be a relative path inside the target, and a source a relative path inside its offering: no leading slash, no drive letter, no backslash, no `..` <a id="cite-steel-2026c"></a>[(Steel, 2026c)](#ref-steel-2026c).

## References

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *Decision: Declared sync policy* (Version 0.2.0) [Unpublished manuscript]. uc-portage. [0001--declared-sync-policy-v0.2.0.md](../../decisions/0001--declared-sync-policy-v0.2.0.md) [↩](#cite-steel-2026a)

<a id="ref-steel-2026b"></a>Steel, C. (2026b). *Decision: One key per axis* (Version 0.2.0) [Unpublished manuscript]. uc-portage. [0002--one-key-per-axis-v0.2.0.md](../../decisions/0002--one-key-per-axis-v0.2.0.md) [↩](#cite-steel-2026b)

<a id="ref-steel-2026c"></a>Steel, C. (2026c). *Decision: Destinations stay inside the target* (Version 0.1.0) [Unpublished manuscript]. uc-portage. [0003--destinations-stay-inside-the-target-v0.1.0.md](../../decisions/0003--destinations-stay-inside-the-target-v0.1.0.md) [↩](#cite-steel-2026c)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.1.0 | 2026-10-09 | Accepted | Initial guide for uc-portage 0.1.0, replacing file-fairy's usage guide |

## License

This document, *Using uc-portage*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
