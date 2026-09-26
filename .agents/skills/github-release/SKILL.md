---
name: github-release
description: Secret scan, status, documentation, changelog, tag, and reproducibility checks.
---

# GitHub Release Skill

This skill governs the preparation, verification, and execution of stable releases for `ai-agent-trading`.

---

## 1. Release Preflight Checklist
Before issuing a release tag or commit, verify the following sequence:

1. **Zero Secret Leaks (Strict)**:
   - Audit `.gitignore` to guarantee `.env`, `*.db`, `backups/`, and credential files are excluded.
   - Run `git status --ignored` to confirm no databases or secrets are tracked or staged.
2. **Version Synchronization**:
   - Check version number match in:
     - `backend/app/core/config.py` (`VERSION`)
     - `backend/pyproject.toml` (`version`)
     - `frontend/package.json` (`version`)
     - `frontend/package-lock.json` (`version`)
3. **Changelog & Documentation**:
   - Update `CHANGELOG.md` following Keep-a-Changelog conventions.
   - Ensure `README.md` reflects current architecture, installation steps, and safety warnings.
4. **Full Test Regression & Static Checks**:
   - 251/251 tests passing (`pytest`).
   - Mypy passing with 0 errors across all source files.
   - Ruff linting passing with 0 warnings.
   - Frontend build passing (`npm run build`).
5. **Clean Clone Reproducibility Gate**:
   - Clone repository to an isolated temporary sandbox (`$env:TEMP`).
   - Run dependencies and test suite to confirm zero machine-specific drift.

---

## 2. Release Execution Commands

```bash
# 1. Review status and stage files
git status
git add -A

# 2. Commit semantic release
git commit -m "release: ai-agent-trading vX.Y.Z"

# 3. Create annotated semantic tag
git tag -a vX.Y.Z -m "ai-agent-trading VX.Y.Z"

# 4. Push to remote (when origin is configured)
git push origin main
git push origin vX.Y.Z
```
