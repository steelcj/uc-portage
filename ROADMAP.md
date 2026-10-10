# Roadmap

Forward plan only; completed items move to [CHANGELOG.md](CHANGELOG.md).

## Next release

- `harvest` writes changes back to the publishing repository's checkout. Whether as a branch, a patch file or both is an open question.

## Later

- The features scheduled by decision 0002, in its order: inline `content` and substitution, then globs, then diff output, along with the `directory` and `touch` states.
- Preserve the executable bit from the source.
- Retract files delivered by an offering that a repository unsubscribes from.
- Verify end to end on macOS and Windows; uc-portage reaches 1.0.0 only when Linux, macOS and Windows are all verified.
