---
title: "Decision: Declared Sync Policy"
dc:title: "Decision: Declared Sync Policy"
dc:creator: "Christopher Steel"
dc:contributor: "Claude (Anthropic) and Claude Opus 5.5 (Anthropic), AI assistance"
dc:subject: "uc-portage, sync modes, mirror, seed_if_missing, overwrite, reference_only, --force"
dc:description: "Sync intent is declared per offering and per item as a sync_mode, not given as a command-line flag; --force is only a one-off override for mirror conflicts, and destructive directory operations are declaration-only."
dc:date: "2026-10-09"
dc:type: "Text"
dc:format: "text/markdown"
dc:identifier: "urn:uuid:d2e61f97-ec1a-470b-b325-604a02379e93"
dc:source: "github.com/steelcj/file-fairy, en/docs/decisions/sync/decision--file-fairy-manifest-declared-sync-policy-v0-1-0.md at commit 4416bcf2c896ce20fee5dc3554bf67f9f5f22cd5, identifier decision--file-fairy-manifest-declared-sync-policy"
dc:language: "en-CA"
dc:rights: "CC-BY-SA-4.0"
sat:version: "0.2.0"
sat:status: "Accepted"
---

# Decision: Declared Sync Policy

Version: 0.2.0
Status: Accepted

## Context

This decision was first made for file-fairy <a id="cite-steel-2026a"></a>[(Steel, 2026a)](#ref-steel-2026a), the tool uc-portage succeeds, and carries over unchanged in substance. In file-fairy a manifest named groups of files to copy; in uc-portage an offering names the files it delivers, and a receiving repository subscribes to it.

file-fairy 0.1.0 classified each item as `new`, `update`, `unchanged`, `conflict` or `missing-source` before applying. It had one way to override its protective default, the global `--force` flag on `apply`, and one way to declare intent, a `reference_only` group setting.

Two limitations followed from that shape.

First, `--force` carries no intent about individual files. It means "for this whole run, also overwrite every item in conflict", where a conflict is a target file edited locally since the last sync. Intent is almost never uniform across a run. A maintainer typically means that the house-style files are theirs to push and the target does not get a vote, that each target owns its own `VERSION` and it must never be stamped over, and that shared documents should update while a local hand-edit stays protected. One global flag cannot express three intents in one apply; it can only turn protection off for all of them at once, which is exactly when it clobbers something the operator did not mean to clobber.

Second, there was no way to say "make sure this file exists, and otherwise leave it alone". A file that should be planted once and then owned by the target, `VERSION` being the canonical example, was overwritten whenever the source changed. On the first apply, with no state record, an existing untracked target file was silently overwritten.

The declaration, now the offering, is what knows which file is which. The flag does not. Intent therefore belongs in the declaration, at the granularity of the file, not in the invocation, at the granularity of the run.

## Decision

Sync intent is declared as a `sync_mode`, set on an offering (inherited by its items) and overridable on each item. When `sync_mode` is absent the behaviour is `mirror`.

| `sync_mode` | Dest missing | Dest present, source changed | Dest present, locally edited |
| --- | --- | --- | --- |
| `mirror` (default) | create | overwrite | protect (conflict, skip) |
| `seed_if_missing` | create | do nothing | do nothing |
| `overwrite` | create | overwrite | overwrite |
| `reference_only` | never touch | never touch | never touch |

`seed_if_missing` decides only on whether the dest path exists, never on the state record or on content. That makes it right for `VERSION` and other files the target owns: planted once when absent, never touched afterwards.

`mirror` treats first contact with an existing, differing dest as a conflict rather than overwriting it, and adopts an existing identical dest.

The `--force` flag is kept only as a one-off override that applies `mirror` conflicts in a single run: "yes, I edited this locally, overwrite it this once". The standing declaration "this file always comes from the source" is `sync_mode: overwrite` in the offering, where it is visible in a diff, reviewable, and scoped to named files.

Destructive directory operations follow the same rule more strictly. Pruning, which deletes files in a target directory that the source no longer contains, must be declared in the offering and must never be reachable through a command-line flag. No one should be able to delete files in a target by typing a flag.

## Alternatives considered

**Keep the global `--force` flag as the intent mechanism.** Rejected. A per-run flag cannot carry per-file intent, so a declaration mixing owned, seeded and protected files forces a choice between under-forcing, and fixing by hand what should have been overwritten, or over-forcing, and clobbering what should have been protected. It also leaves no trace in the repository.

**Remove `--force` entirely.** Rejected, though close. It is the cleaner end state, but it drops the legitimate one-off case of discarding a local edit to a `mirror` file once, which does not justify reclassifying the file as `overwrite`.

**Add a seed subcommand instead of a mode.** Rejected for the same reason as keeping `--force`: a verb works at the granularity of the run, but the intent belongs to the file.

## Consequences

- `offering.schema.yaml` allows `sync_mode` on an offering and on each item, the item overriding the offering; absence means `mirror`.
- The planner computes each item's status from its effective mode, and only `mirror` items can be in conflict.
- `--force` is documented as a one-off override for `mirror` conflicts and points at `sync_mode: overwrite` for the standing case.
- Directory syncing and pruning, when they arrive, are declaration-only.

## References

<a id="ref-steel-2026a"></a>Steel, C. (2026a). *file-fairy* (Version 0.7.0) [Computer software]. GitHub. https://github.com/steelcj/file-fairy [↩](#cite-steel-2026a)

## Changelog

| Version | Date | Status | Notes |
| --- | --- | --- | --- |
| 0.2.0 | 2026-10-09 | Accepted | Migrated from file-fairy to uc-portage: manifests and groups become offerings, a new urn:uuid with the old identifier in dc:source, relicensed CC-BY-SA-4.0, mirror's first-contact protection recorded, prose unwrapped |
| 0.1.0 | 2026-08-02 | Draft | Initial draft in file-fairy: declared sync_mode vocabulary, --force demoted to a one-off mirror override, pruning declaration-only |

## License

This document, *Decision: Declared Sync Policy*, by **Christopher Steel**, with AI assistance from **Claude (Anthropic)** and **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
