# Release Checklist

Use this checklist before publishing a public release. Do not create or push a
tag until the repository state, quality checks, and GitHub workflow runs have
all been reviewed.

## Repository

- [ ] Working tree clean
- [ ] README polished
- [ ] Architecture documented
- [ ] Project structure documented
- [ ] Screenshots added
- [ ] Licence present
- [ ] Changelog current

## Quality

- [ ] Local tests pass
- [ ] `compileall` passes
- [ ] Docker tests pass
- [ ] Smoke test passes
- [ ] GitHub Actions Python job green
- [ ] GitHub Actions Docker job green

## Security and Privacy

- [ ] No `.env` committed
- [ ] No tokens or credentials
- [ ] No private contact data
- [ ] Only fictional demo data committed
- [ ] Generated output ignored

## Versioning

- [ ] Package version confirmed
- [ ] Release tag matches package version
- [ ] Release notes reviewed

## GitHub

- [ ] Repository description set
- [ ] Topics added
- [ ] Default branch `main`
- [ ] Release created
- [ ] Tag pushed
- [ ] CI badge green

## Release Commands

For the current package version `0.1.0`, use release tag `v0.1.0`.

Run these checks before tagging:

```bash
git status
git switch main
git pull --ff-only
python -m pytest -q
python -m compileall src tests
bash scripts/docker-smoke-test.sh
```

Create and push the tag only after the checklist is complete:

```bash
git tag -a v0.1.0 -m "Smart Infrastructure Lead Intelligence v0.1.0"
git push origin v0.1.0
```

## GitHub Release

Create the GitHub release manually after CI is green:

1. Open the repository on GitHub.
2. Open Releases.
3. Draft a new release.
4. Choose `v0.1.0`.
5. Set the title to `Smart Infrastructure Lead Intelligence v0.1.0`.
6. Paste `.github/release-notes-v0.1.0.md`.
7. Mark as latest release.
8. Publish only after CI is green.
