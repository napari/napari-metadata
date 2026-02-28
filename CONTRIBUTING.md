# Contributing Guide

We welcome your contributions! Please see the provided steps below and never hesitate to contact us.

If you are a new user, we recommend checking out the detailed [Github Guides](https://guides.github.com).

## Setting up a development installation

In order to make changes to `napari-metadata`, you will need to [fork](https://guides.github.com/activities/forking/#fork) the
[repository](https://github.com/napari/napari-metadata).

If you are not familiar with `git`, we recommend reading up on [this guide](https://guides.github.com/introduction/git-handbook/#basic-git).

Clone the forked repository to your local machine and change directories:
```sh
git clone https://github.com/your-username/napari-metadata.git
cd napari-metadata
```

Set the `upstream` remote to the base `napari-metadata` repository:
```sh
git remote add upstream https://github.com/napari/napari-metadata.git
```

Install the package in editable mode, along with all of the developer tools
using [`uv`](https://docs.astral.sh/uv/):
```sh
uv pip install -e . --group dev
```

Or equivalently with `pip`:
```sh
pip install -e . --group dev
```

We use pre-commit hooks to format and lint code automatically prior to each
commit. The hooks are configured in `.pre-commit-config.yaml` and run `ruff`
for formatting and linting, among other checks.

We recommend using [`prek`](https://github.com/j178/prek), a faster
drop-in replacement for `pre-commit` written in Rust with no Python runtime
dependency. `prek` is included with the development dependencies.
Register the git hooks with:

```sh
prek install
```

Upon committing, your code will be formatted and linted according to our
[`ruff` configuration](https://github.com/napari/napari-metadata/blob/main/pyproject.toml).
To learn more, see [`ruff`'s documentation](https://docs.astral.sh/ruff/).

You can run all hooks against the entire codebase at any time:

```sh
prek run --all-files
```

If you wish to tell the linter to ignore a specific line use the `# noqa`
comment along with the specific error code (e.g. `import sys  # noqa: E402`) but
please do not ignore errors lightly.

## Making changes

Create a new feature branch:

```sh
git checkout main -b your-branch-name
```

`git` will automatically detect changes to a repository.
You can view them with:

```sh
git status
```

Add and commit your changed files:
```sh
git add my-file-or-directory
git commit -m "my message"
```

## Tests

We use unit tests to ensure that
napari-metadata works as intended. Writing tests for new code is a critical part of
keeping napari-metadata maintainable as it grows.

Run tests using `tox` (which uses `uv` under the hood via `tox-uv`):

```sh
uvx --with tox-gh-actions tox
```

Or run `pytest` directly after installing development dependencies:

```sh
pytest
```

### Help us make sure it's you

Each commit you make must have a [GitHub-registered email](https://github.com/settings/emails)
as the `author`. You can read more [here](https://help.github.com/en/github/setting-up-and-managing-your-github-user-account/setting-your-commit-email-address).

To set it, use `git config --global user.email your-address@example.com`.

## Keeping your branches up-to-date

Switch to the `main` branch:
```sh
git checkout main
```

Fetch changes and update `main`:
```sh
git pull upstream main --tags
```

This is shorthand for:
```sh
git fetch upstream main --tags
git merge upstream/main
```

Update your other branches:
```sh
git checkout your-branch-name
git merge main
```

## Sharing your changes

Update your remote branch:
```sh
git push -u origin your-branch-name
```

You can then make a [pull-request](https://guides.github.com/activities/forking/#making-a-pull-request) to `napari-metadata`'s `main` branch.

## Building the docs

Install [pixi](https://pixi.sh), then from the project root:

```sh
pixi run docs-build
```

The docs will be built at `docs/_build`.
Most web browsers will also allow you to preview HTML pages directly.
Try entering `file:///absolute/path/to/napari-metadata/docs/_build/index.html` in your address bar.


You can preview with a live-reloading server that opens automatically:

```sh
pixi run docs-live
```

## Code of conduct

`napari` has a [Code of Conduct](https://napari.org/stable/community/code_of_conduct.html) that should be honored by everyone who participates in the `napari` community, including `napari-metadata`.

## Questions, comments, and feedback

If you have questions, comments, suggestions for improvement, or any other inquiries
regarding the project, feel free to open an [issue](https://github.com/napari/napari-metadata/issues).

Issues and pull-requests are written in [Markdown](https://guides.github.com/features/mastering-markdown/#what). You can find a comprehensive guide [here](https://guides.github.com/features/mastering-markdown/#syntax).
