# Roadmap

Forward plan only; completed items move to [CHANGELOG.md](CHANGELOG.md).

## Next release

Scope approved on 2026-10-11 for 0.2.0:

- Guarded retraction (decision 0004): an optional `accepted_sha256` list on retraction items, removal only on a matching normalised checksum, and "retained: content differs from every known version" reported by plan, apply and harvest. Ships together with uc-automa 0.2.0's first offering that uses it.
- `[tool.uc-automa.release]` pins in `pyproject.toml`, and the README's `Install offline` section (uc-automa 0028).
- The README's `Get the release key` section (uc-automa 0030), before `Install offline`, and tag verification documented for Linux and macOS only, with the Windows gap stated (uc-automa 0032).
- Release order, approved on 2026-10-11: uc-portage 0.2.0 is cut and published first, with the ceremony of uc-automa's candidate commit installed editable; that candidate already depends on `uc-portage>=0.2.0,<0.3.0` and its README names `uc-portage@v0.2.0`. uc-automa 0.2.0's release commit is that candidate commit plus the cut, and nothing else. If it differs, uc-portage's release runs are repeated with the new uc-automa commit.
- Before each tag is pushed, verification runs on Linux and Windows (uc-automa 0027), and the release wheels match their records (uc-automa 0028).

## Later

- In 0.3.0: `harvest` writes changes back to the publishing repository's checkout. Whether as a branch, a patch file or both is an open question.
- The features scheduled by decision 0002, in its order: inline `content` and substitution, then globs, then diff output, along with the `directory` and `touch` states.
- Preserve the executable bit from the source.
- Retract files delivered by an offering that a repository unsubscribes from.
- Verify end to end on macOS and Windows; uc-portage reaches 1.0.0 only when Linux, macOS and Windows are all verified.
