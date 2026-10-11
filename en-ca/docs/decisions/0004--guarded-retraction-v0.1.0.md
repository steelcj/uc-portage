---
title: "Decision: Guarded Retraction"
dc:title: "Decision: Guarded Retraction"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "uc-portage, retraction, state: absent, checksums, accepted_sha256, harvest"
dc:description: "A retraction item may carry the checksums of every content its publisher delivered; with them, a file is removed only if its content matches one, and is otherwise retained and reported. This adds a ruling to uc-portage 0002 and leaves ruling 3 unchanged for items without checksums."
dc:date: "2026-10-11"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:3d6a57a6-65a3-48ec-ba23-ee5088b09a30"
dc:relation: "urn:uuid:902f6797-c2ff-45de-8c78-deb172205f20"
dc:language: "en-CA"
dc:rights: "CC-BY-4.0"
sat:version: "0.1.0"
sat:status: "Accepted"
---

# Decision: Guarded Retraction

Version: 0.1.0
Status: Accepted

## Context

uc-portage 0002 settled how retraction works: `state: absent` applies to any declared destination, whether or not uc-portage delivered it, and a declared file that exists is deleted <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a). That is right for files only an offering ever wrote. It is not safe for files a predecessor copied into repositories, such as the release scripts and guides the old automa distributed: a repository may have edited its copy, and an edited copy may hold work, or an improvement worth sending back. uc-automa's release ceremony retires those copies by offering <a id="cite-steel-2026b"></a>[(Steel, 2026b)](#ref-steel-2026b), so retraction needs a way to remove a copy only when it is unchanged.

## Decision

This adds a ruling to uc-portage 0002. It does not supersede it, and it does not change ruling 3.

- **A retraction may carry known checksums.** An item with `state: absent` may list `accepted_sha256`, the SHA-256 checksums of every content its publisher actually delivered at that path.
- **With the list, retraction is guarded.** The file is removed only if its content, normalised for line endings as every uc-portage checksum is, matches one of the listed checksums. A CRLF checkout of an unchanged file still matches. Otherwise the file is left in place and reported: "retained: content differs from every known version".
- **Without the list, ruling 3 applies unchanged.** A declared file that exists is retracted, whatever its content.
- **A missing file** is reported as retired, with or without a list.
- **Retained files are reported by `plan`, `apply` and `harvest`.** In harvest, a locally edited copy of something being retired may hold an improvement worth reviewing.
- **uc-portage stays generic.** The checksums come from the offering; uc-portage reads no predecessor's records.

## Consequences

- `schemas/offering.schema.yaml` gains the optional `accepted_sha256` list on retraction items, in uc-portage 0.2.0, together with the guard. The first offering that uses it ships in uc-automa 0.2.0, which requires uc-portage 0.2.0 or later.
- uc-portage 0.1.0 cannot apply a guarded retraction unguarded. Its schema allows no other key on a retraction item, so it refuses the whole offering before planning. This was checked on 2026-10-11 against the published v0.1.0: both `plan` and `apply` refused, and the file was left in place.
- A publisher retiring files computes the list from what it actually delivered, and records how, so the list can be recomputed.

## References

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *Decision: One key per axis* (Version 0.2.0) [Decision record]. uc-portage. [0002--one-key-per-axis-v0.2.0.md](0002--one-key-per-axis-v0.2.0.md) [↩](#cite-steel-2026a)

<a id="ref-steel-2026b"></a>Steel, C. (2026b). *Decision: Release ceremony* (Version 0.1.0) [Decision record]. uc-automa 0026. https://github.com/steelcj/uc-automa [↩](#cite-steel-2026b)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.1.0 | 2026-10-11 | Accepted | Initial version |

## License

This document, *Decision: Guarded Retraction*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
