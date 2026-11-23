# Contributing to design3d

First off, thanks for taking the time to contribute! 

All types of contributions are encouraged and valued. The community looks forward to your contributions. 

> And if you like the project, but just don't have time to contribute, that's fine. There are other easy ways to support the project and show your appreciation, which we would also be very happy about:
> - Use design3d in your projects!
> - Star the project
> - Talk about it
> - Refer this project in your project's readme
> - Mention the project at local meetups and tell your friends/colleagues


## I want to contribute to the code

### Ask before coding

If you are not sure about your contribution you can ask the question on the issues or MP the project leader.

### Process

Start your branch from `master` and open your pull request against `master`. Releases are tagged on `master`.

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
- Add user-facing changes to `CHANGELOG.md`, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- When fixing a bug, first add a test that reproduces it.

### Running checks locally

```bash
pip install -e '.[test,doc]'
pre-commit run --all-files
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -m unittest discover -v tests
coverage run --rcfile=.coveragerc --data-file=.coverage --source=design3d -a scripts/ci_scripts.py
coverage report
coverage json --data-file=.coverage -o coverage.json
python check_coverage.py coverage.json
make -C docs html SPHINXOPTS="-W --keep-going"
```

`scripts/ci_scripts.py` runs scripts that call `babylonjs()`, which opens a browser. Set `BROWSER=true` to avoid opening
browser tabs when running them locally.

### CI

Your contribution may be refused by our CI. In this case:

- pre-commit hooks fail (black, codespell, cython-lint): run `pre-commit run --all-files`
- a test or a CI script fails: fix it, or add a test for the new behavior
- the coverage of the project or of a file drops below its threshold in `check_coverage.py`: add some tests
- the documentation build emits a Sphinx warning: fix the docstring or page

Correct the CI errors to get approval from design3d team!

## I Have a Question

Before you ask a question, it is best to search for existing [Issues](/issues) that might help you. In case you have found a suitable issue and still need clarification, you can write your question in this issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions , depending on what seems relevant.
- Put the label "Question" to your issue
