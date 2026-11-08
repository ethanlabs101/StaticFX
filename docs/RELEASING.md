# Releasing

Releases go to [PyPI](https://pypi.org/project/staticfx/) automatically when a
version tag is pushed. The workflow is `.github/workflows/release.yml`.

## One-time setup

PyPI is told to trust this repository's release workflow, so no API token is
ever stored in GitHub.

1. Create an account on [pypi.org](https://pypi.org) and turn on two-factor
   authentication (PyPI requires it to publish).
2. Go to **Your projects → Publishing** (pypi.org/manage/account/publishing)
   and add a *pending publisher* for a new project:

   Field | Value
   --- | ---
   PyPI project name | `staticfx`
   Owner | `ethanlabs101`
   Repository name | `StaticFX`
   Workflow name | `release.yml`
   Environment name | `pypi`

   "Pending" means the project doesn't exist yet; the first successful
   release creates it.
3. In the GitHub repository, open **Settings → Environments**, create an
   environment called `pypi`, and (optionally) add yourself as a required
   reviewer so every release waits for your click.

## Each release

1. Update `__version__` in `staticfx/__init__.py` (`pyproject.toml` reads it
   from there).
2. Move the changes under a new heading in `CHANGELOG.md`.
3. Commit, then tag and push:

   ```bash
   git tag v2.0.1
   git push origin main v2.0.1
   ```

The workflow checks that the tag matches `__version__`, runs the tests,
builds the wheel and source archive, checks them with `twine`, publishes to
PyPI, and creates a GitHub release with the same files attached. A few
minutes later `pipx install staticfx` gets the new version.

Versions follow [semantic versioning](https://semver.org): a bug fix bumps
the last number, a new feature the middle one, and anything that breaks saved
files or command-line scripts the first.

## Checking a build locally

```bash
pip install build twine
python -m build
twine check --strict dist/*
pipx install dist/staticfx-*.whl --force   # try the real installed command
```
