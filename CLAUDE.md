# uc-portage

uc-portage is a generic, declarative file reconciler: it carries offerings into a repository and reports changes worth sending back. It must stay generic, so nothing in it may depend on uc-automa or name Vishpala's offerings.

## Working here

- Python 3.8 or later, standard library plus PyYAML, `pathlib` throughout, no shell commands.
- Run `python3 -m unittest discover -s tests` before every commit.
- The engine's semantics are set by the decisions in `en-ca/docs/decisions/`; change them only through a new version of a decision.
- `schemas/offering.schema.yaml` is the contract for offerings. uc-automa reads it from here; it is never copied.
- Ask before pushing, tagging or changing any other repository.
