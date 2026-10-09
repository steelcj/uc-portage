---
title: "Decision: One Key per Axis"
dc:title: "Decision: One Key per Axis"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Fable 5 (Anthropic) and Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "uc-portage, offering format, state, source, sync_mode, managed blocks, retraction"
dc:description: "Each axis of an item is exactly one key: state, source or content, sync_mode, and glob with exclude; managed blocks are their own item shape; and five rulings settle markers, substitution, retraction, glob reporting and implementation order."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:902f6797-c2ff-45de-8c78-deb172205f20"
dc:source: "github.com/steelcj/file-fairy, en/docs/decisions/sync/decision--manifest-organization-one-key-per-axis-v0-1-0.md at commit 4416bcf2c896ce20fee5dc3554bf67f9f5f22cd5, identifier decision--manifest-organization-one-key-per-axis"
dc:relation: "urn:uuid:d2e61f97-ec1a-470b-b325-604a02379e93"
dc:language: "en-CA"
dc:rights: "CC-BY-SA-4.0"
sat:version: "0.2.0"
sat:status: "Accepted"
---

# Decision: One Key per Axis

Version: 0.2.0
Status: Accepted

## Context

This decision was first made for file-fairy's manifests and carries over to uc-portage's offerings. A design document in file-fairy <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a) proposed how items are organised, showed a full worked example and listed five open rulings. This record ratifies it. The design document stays in file-fairy's history as the full worked reference.

## Decision

Each axis of an item is exactly one item-level key, and no key answers two questions:

| Axis | Key | Values |
| --- | --- | --- |
| Type and existence | `state` | `file` (default), `directory`, `absent` |
| Provenance | `source`, or inline `content`, never both | a path, or text |
| Reconciliation | `sync_mode` | as in the declared sync policy <a id="cite-steel-2026b"></a>[(Steel, 2026b)](#ref-steel-2026b) |
| Discovery | `glob` with `exclude` | patterns |

The executable bit is preserved from the source unconditionally, as a behaviour rather than a declaration. A managed block is its own item shape, because a region is not a file. Defaults are the existing behaviour, so an item that names none of the newer keys keeps its meaning.

The five rulings, each decided as the design recommended:

- Block markers are HTML comments, invisible in rendered Markdown and visible in source. In uc-portage they read `<!-- uc-portage:begin NAME -->` and `<!-- uc-portage:end NAME -->`.
- `substitute: true` is an explicit opt-in on each item. Substituting automatically wherever variables exist is rejected as action at a distance.
- `state: absent` applies to any declared dest, whether or not uc-portage ever delivered it. Retractions always appear in their own section of the plan.
- `plan` reports items entering or leaving a glob's match set explicitly; a widening glob is never silent.
- Implementation order: `absent`, then managed blocks, then `content` and substitution, then globs, then diff output.

## Consequences

- `absent` and managed blocks are implemented, carried over from file-fairy. `content`, substitution, globs, the `directory` and `touch` states and diff output are not, and an offering that uses them is refused by name as scheduled rather than as unknown.
- Preserving the executable bit is not yet implemented: file-fairy copied content only, and uc-portage 0.1.0 does the same.
- `offering.schema.yaml` gives each item one of three shapes, file, block or absent, and grows a shape or a key as each scheduled feature lands.
- The alternatives the design weighed, such as verb-shaped groups, mode bundles, reconciliation folded into `state` and blocks as a key on file items, are recorded in the design document with the reasons they lost, and are not reopened by implementation details.

## References

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *Design: Manifest organization for accepted features* (Version 0.1.0) [Unpublished manuscript]. file-fairy, en/docs/design/. https://github.com/steelcj/file-fairy [↩](#cite-steel-2026a)

<a id="ref-steel-2026b"></a>Steel, C. (2026b). *Decision: Declared sync policy* (Version 0.2.0) [Unpublished manuscript]. uc-portage. [0001--declared-sync-policy-v0.2.0.md](0001--declared-sync-policy-v0.2.0.md) [↩](#cite-steel-2026b)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.2.0 | 2026-10-09 | Accepted | Migrated from file-fairy to uc-portage: manifests become offerings, markers renamed to uc-portage, implementation state recorded, a new urn:uuid with the old identifier in dc:source, relicensed CC-BY-SA-4.0 |
| 0.1.0 | 2026-08-03 | Draft | Initial record in file-fairy, ratifying the design and its five recommendations; absent-first order confirmed |

## License

This document, *Decision: One Key per Axis*, by **Christopher Steel**, with AI assistance from **Claude Fable 5 (Anthropic)** and **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
