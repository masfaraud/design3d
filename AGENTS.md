# Instructions for LLM agents

These rules apply to any AI coding agent working on design3d.

## Review: show a commented diff before committing

- Before committing, show the diff to the maintainer and wait for validation.
- Comment every non-trivial part of the diff: what changed, why, and what it fixes or how it behaves differently.
  Trivial parts (renames, formatting, imports) can be summarized in one line instead of being shown in full.
- Do not commit or push until the maintainer has approved the diff.
- Stage files explicitly by path. Never commit generated files (test or script outputs such as `.step`, `.stp`,
  `.stl`, `.html`).

## Bugs: reproduce with a failing test first

When a bug is identified:

1. Write a test that reproduces it, and check that this test fails on the current code.
2. Fix the bug.
3. Check that the new test passes, and that the rest of the test suite still passes.

Do not adjust expected values in existing tests to make them pass without understanding why they changed. If an
expected value was produced by a buggy behavior, explain it in the commented diff before changing it.

## Commits and changelog

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
  `type(optional scope): description`, with types such as `feat`, `fix`, `refactor`, `test`, `docs`, `build`,
  `ci`, `chore`.
- Keep one topic per commit.
- Update `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): add user-facing
  changes to the unreleased section, under the matching heading (`Added`, `Changed`, `Deprecated`, `Removed`,
  `Fixed`, `Security`).

## Coverage

- Never lower the coverage thresholds (`MIN_PROJECT_COVERAGE` and `MIN_FILE_COVERAGE` in `coverage.py`).
- Each change should keep or improve coverage: add tests for new and modified code.
- When coverage has increased above a threshold, raise that threshold accordingly.

## Running checks locally

```bash
pre-commit run --all-files
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -m unittest discover -v tests
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -a scripts/ci_scripts.py
coverage report
```

`scripts/ci_scripts.py` runs scripts that call `babylonjs()`, which opens a browser. Set `BROWSER=true` to
avoid opening browser tabs when running them locally.
