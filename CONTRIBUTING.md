# Contributing to pyStrich

Thanks for your interest in pyStrich! Contributions of all kinds are welcome —
bug reports, documentation fixes, new symbologies and everything in between.

This project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md); by
participating you are expected to uphold it.

## Resources

- **Documentation:** https://www.method-b.uk/pyStrich/docs/
- **Issue tracker:** https://github.com/mmulqueen/pyStrich/issues
- **Package:** https://pypi.org/project/pyStrich/

## Getting set up

pyStrich uses [uv](https://docs.astral.sh/uv/) for dependency management and
[pre-commit](https://pre-commit.com/) for local checks.

```bash
uv sync --group dev          # install the project and its dev dependencies
uv run pre-commit install    # install the git hook
```

The pre-commit hook mirrors the CI QA and runs on every commit: `ruff check`,
`ruff format`, `mypy` and `pytest`. To run it by hand:

```bash
uv run pre-commit run --all-files
```

## Running the full checks

CI tests against every supported Python version. To reproduce that locally you
need [podman](https://podman.io/); the scripts build throwaway images so nothing
is installed on your host:

```bash
./scripts/test-python-versions.sh   # ruff, mypy and pytest across the matrix
./scripts/build-docs.sh             # build the documentation
```

For a quick one-off check on your own Python, `uv run pytest` is enough.

## Submitting changes

- Branch off `main` and open a pull request against `main`.
- Keep pull requests focused on a single change; separate unrelated work.
- Make sure the pre-commit checks pass before pushing — CI runs the same ones.
- Add or update tests for any behaviour you change, and update the docs under
  `docs/` when user-facing behaviour changes.

## Reporting bugs

Open an issue with:

- the pyStrich and Python versions you are using,
- the symbology and options involved,
- a minimal snippet that reproduces the problem, and
- what you expected to happen versus what actually happened.

## Requesting features

Feature requests are welcome as issues. Please describe the use case — for a new
symbology, a link to the relevant specification is very helpful.

## New symbologies

Before spending time on adding support for a new symbology, please raise an issue
or discuss it with the maintainers. It is our policy to support major symbologies
that are in current mainstream use, standardised, and have an ecosystem of
decoders. We generally won't add support for niche, emerging or declining
symbologies, or for non-standard extensions.

## AI-assisted contributions

While we understand that many software developers are now AI-assisted, we expect
that all contributions are reviewed and understood by a human contributor before
they're submitted. We reserve the right to reject AI drivebys without discussion.

## Independent implementation

pyStrich seeks to develop as an independent implementation. We verify our output
against decoders such as zxing-cpp and dmtxread, but it is our policy not to
copy or port the encoding behaviour of other libraries — we build from the
ground up. This does not preclude surveying the implementations of other
decoders and encoders.

## Coding standards

- Formatting and linting are handled by ruff; type checking by mypy in strict
  mode. The pre-commit hook enforces both.
- Prose in code and docs is written in British English. Public identifiers
  (keyword arguments, option names, attributes) use spellings that are the same
  in British and American English where possible.

## Recognition

Contributors are credited on the
[contributors page](https://www.method-b.uk/pyStrich/docs/contributors.html).
Thank you for helping improve pyStrich.

## Licence

pyStrich is released under the Apache License, Version 2.0. By contributing you
agree that your contributions are licensed under the same terms.
