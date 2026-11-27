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
3. Check that the new test passes, and that the tests related to the change still pass.

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

## Pull requests

- Open pull requests against `master` (`gh pr create --base master`), from a branch created from an up-to-date
  `origin/master`, even when the work was started from another branch or worktree.
- Do not target another feature branch, and do not stack a pull request on an unmerged one: a follow-up found
  while working on a pull request goes in its own pull request against `master`.

## Coverage

- Never lower the coverage thresholds (`MIN_PROJECT_COVERAGE` and `MIN_FILE_COVERAGE` in `check_coverage.py`).
- Each change should keep or improve coverage: add tests for new and modified code.
- When coverage has increased above a threshold (as reported by the CI), raise that threshold accordingly.

## Running checks locally

To keep the work interactive, do not run the whole test suite, the CI scripts or the coverage check locally: run
only the tests related to the change, that is the test files of the modified modules and classes, the new tests, and
the tests of the code that calls the modified code. Run `pre-commit` on the modified files only. The CI runs the
whole test suite, the scripts and the coverage check on the pull request.

```bash
pre-commit run --files path/to/modified_file.py tests/path/to/test_file.py
python -m unittest tests.wires.test_contour2d tests.primitives2d.test_slot2d
```

The full checks, run by the CI, for when the maintainer asks for them:

```bash
pre-commit run --all-files
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -m unittest discover -v tests
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -a scripts/ci_scripts.py
coverage report
coverage json --data-file=.coverage -o coverage.json
python check_coverage.py coverage.json
```

`scripts/ci_scripts.py` runs scripts that call `babylonjs()`, which opens a browser. Set `BROWSER=true` to
avoid opening browser tabs when running them locally.
