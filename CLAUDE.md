# uc-portage

uc-portage is a generic, declarative file reconciler: it carries offerings into a repository and reports changes worth sending back. It must stay generic, so nothing in it may depend on uc-automa or name Vishpala's offerings.

## Working here

- Python 3.8 or later, standard library plus PyYAML, `pathlib` throughout, no shell commands.
- Run `python3 -m unittest discover -s tests` before every commit.
- The engine's semantics are set by the decisions in `en-ca/docs/decisions/`; change them only through a new version of a decision.
- `schemas/offering.schema.yaml` is the contract for offerings. uc-automa reads it from here; it is never copied.
- Ask before pushing, tagging or changing any other repository.

<!-- uc-portage:begin uc-automa-signpost -->
## uc-automa

This repository follows uc-automa at the version pinned in `.uc-automa.yaml`.

- The rules are uc-automa's directives, under `en-ca/docs/directives/` at that version. Each names the check that enforces it, if it has one.
- Run `uc-automa check` before committing, and `uc-automa offerings plan` to see whether shared files have drifted.
- Files the layout marks `from_offering` arrive from uc-automa; change them there, not here.
- If a rule is not written in a directive, ask. Never copy a convention from another repository.
<!-- uc-portage:end uc-automa-signpost -->
