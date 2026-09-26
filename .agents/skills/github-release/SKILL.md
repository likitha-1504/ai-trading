---
name: github-release
description: Secret scan, status, documentation, changelog, tag, and reproducibility checks.
---

# GitHub Release Skill

This skill governs the release preparation, version tagging, and secret hygiene for `ai-agent-trading`.

## Principles
1. **Zero Secret Leaks**: Audit `.gitignore` and staged files to guarantee no `.env`, `.db`, `.key`, or credentials enter git.
2. **Version Bump Discipline**: Synchronize versions across `pyproject.toml`, `config.py`, and `package.json`.
3. **Changelog Maintenance**: Document changes under Keep a Changelog guidelines in `CHANGELOG.md`.
4. **Reproducibility Verification**: Verify a clean clone installs dependencies, passes tests, and launches cleanly.
5. **Signed / Annotated Tags**: Use semantic tags (e.g., `v1.0.0`) matching release commits.
