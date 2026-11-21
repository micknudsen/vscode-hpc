# Contributing to vscode-hpc

Branch from current `master` and contribute through a pull request. Include the
behavior change, relevant issue, and commands and results used to verify it.
All contributors, maintainers, and automation follow the same workflow.

The active **Protect master** GitHub ruleset requires an up-to-date branch and
all configured CI checks to pass before merging. Only squash merges are allowed;
history remains linear. Force pushes to `master`, deletion of `master`, and
bypasses are disabled. Resolve review conversations before merging. Reviewer
approval is optional, as in `codex-hpc`. Merged feature branches are deleted.

## Verification

Install a wheel built from the source distribution and run the tests:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip build
.venv/bin/python -m build
.venv/bin/python -m pip install --force-reinstall --no-deps dist/*.whl
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m unittest discover -s tests -v
```

Tests invoke the installed public CLI using controlled SSH and VS Code peers;
they do not submit jobs to a real cluster. CI tests Python 3.9 and 3.14 on Linux
and macOS, builds the source distribution, wheel and Conda package, then installs
the same Conda package in fresh Linux and macOS environments and runs the suite.

The required checks are the four **Product tests** matrix jobs, **Build
distributions**, both **Conda tests** matrix jobs, and **CI passed**. The final
gate fails if a dependency fails, is skipped, or is cancelled. When adding or
renaming CI jobs, update the gate dependencies and the GitHub ruleset before
merging. Keep CI running for every PR; do not add path filters that omit checks.

## Delivery

After pushing a feature branch, inspect all CI on its current head. Fix failures
on that branch and wait for the new checks. Update from `master` if required.
Verify the active protection and merge only the checked head using a squash
merge. Verify post-merge CI too. Fix regressions through another PR; preserve
protection throughout. A request to prepare a PR alone does not authorize merging.

For versioned publication, follow [Releasing](../docs/releasing.md).
