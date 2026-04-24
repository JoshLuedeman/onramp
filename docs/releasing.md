# Versioning & Release Strategy

## Semantic Versioning

OnRamp follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** — Breaking changes to the API, database schema (without migration), or deployment model
- **MINOR** — New features, new API endpoints, new CAF design area coverage
- **PATCH** — Bug fixes, documentation updates, dependency patches

## Version Milestone Mapping

| Version | Milestone | Focus |
|---------|-----------|-------|
| 0.13.0 | M0 | UX Agent Setup — core scaffold and feature set |
| 0.14.0 | M1 | Critical Security & Stability |
| 0.15.0 | M2 | Test Coverage & Quality |
| 0.16.0 | M3 | Backend Code Quality |
| 0.17.0 | M4 | Frontend Quality & UX |
| 0.18.0 | M5 | Infrastructure & CI/CD Hardening |
| 0.19.0 | M6 | Documentation & Repository Health |
| 1.0.0 | GA | Production-ready release |

## Release Process

1. **Create a release branch** from `main`:
   ```bash
   git checkout -b release/v0.19.0
   ```

2. **Update version references**:
   - Update `CHANGELOG.md`: move `[Unreleased]` items under the new version heading with the release date
   - Verify version in `backend/pyproject.toml` and `frontend/package.json` if applicable

3. **Open a pull request** targeting `main`:
   - Title: `release: v0.19.0`
   - Description: summary of changes from the changelog
   - All CI checks must pass (lint, test, build, Bicep validation)

4. **Review and merge** the release PR.

5. **Tag the release** on the merge commit:
   ```bash
   git tag -a v0.19.0 -m "v0.19.0 — M6 Documentation & Repository Health"
   git push origin v0.19.0
   ```

6. **Create a GitHub Release** from the tag:
   - Title: `v0.19.0 — M6 Documentation & Repository Health`
   - Body: copy the relevant `CHANGELOG.md` section
   - Attach any build artifacts if applicable

## Pre-Release Checklist

- [ ] All CI checks pass on the release branch
- [ ] `CHANGELOG.md` is up to date with all changes since the last release
- [ ] No open blockers or critical bugs for the milestone
- [ ] Documentation reflects the current state of the application
- [ ] Version references are consistent across the codebase

## Hotfix Releases

For critical production fixes:

1. Branch from the release tag: `git checkout -b hotfix/v0.18.1 v0.18.0`
2. Apply the fix with tests
3. Follow the standard release process with a PATCH version bump
