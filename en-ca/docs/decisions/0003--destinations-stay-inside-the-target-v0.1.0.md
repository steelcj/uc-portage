---
title: "Decision: Destinations Stay Inside the Target"
dc:title: "Decision: Destinations Stay Inside the Target"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "uc-portage, offerings, destination paths, path containment, pull model, harvest"
dc:description: "Every destination an offering names must be a relative path inside the receiving repository; this reverses file-fairy's deliberate choice to trust manifest paths as written."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:42bf1203-e493-41db-a93e-0428d75d9217"
dc:relation: "urn:uuid:d2e61f97-ec1a-470b-b325-604a02379e93"
dc:language: "en-CA"
dc:rights: "CC-BY-4.0"
sat:version: "0.1.0"
sat:status: "Accepted"
---

# Decision: Destinations Stay Inside the Target

Version: 0.1.0
Status: Accepted

## Context

file-fairy deliberately had no check that a destination stayed inside the target. Its source code recorded why: the manifest was a configuration file the operator wrote for themselves, not adversarial input, so it was trusted and executed as written, and checksums existed for drift detection rather than for safety <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a).

Two things have changed. Under the pull model, a receiving repository subscribes to offerings published by another repository, so the paths uc-portage writes to are no longer written by the person running it. And harvest is planned to write changes back to the publishing repository, so paths will cross between repositories in both directions.

## Decision

Every `dest` in an offering must be a relative path inside the receiving repository, written with forward slashes: no leading slash, no drive letter, no backslash and no `..` part. `offering.schema.yaml` states the rule, and the engine checks it again before planning, so an offering that breaks it is refused before anything is written. Source paths follow the same rule, relative to the offering's own directory.

## Alternatives considered

**Keep trusting declarations as written.** Rejected. The trust rested on the operator writing the manifest, which is no longer true when the offering comes from another repository.

**Check only when applying.** Rejected. A plan that names a path outside the target is already wrong, and refusing it at plan time means the mistake is seen before anything is written.

## Consequences

- An offering that escapes the target fails validation and is refused with a message naming the destination.
- The same paths are valid on Linux, macOS and Windows, because drive letters and backslashes are refused everywhere.
- When harvest learns to write back, it relies on the same containment for paths in the publishing repository.

## References

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *file-fairy* (Version 0.7.0) [Computer software]. GitHub. https://github.com/steelcj/file-fairy [↩](#cite-steel-2026a)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.1.0 | 2026-10-09 | Accepted | Initial decision: destinations and sources stay inside their roots, reversing file-fairy's design note |

## License

This document, *Decision: Destinations Stay Inside the Target*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).
