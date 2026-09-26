---
name: deployment-review
description: Environment variables, dependencies, persistence, health checks, and free-tier constraints.
---

# Deployment Review Skill

This skill governs deployment safety reviews and infrastructure validation for `ai-agent-trading`.

## Principles
1. **Free-Tier Constraints**: Verify that live trading does not depend on sleeping or throttled cloud services.
2. **Database Persistence**: Ensure SQLite WAL files and backup volumes reside on persistent block storage.
3. **Health Probes**: Validate that DB WAL, disk space, backup freshness, Watcher SLA, broker connectivity, and AI Council are healthy.
4. **Environment Integrity**: Ensure `.env` files are properly configured and operational secrets are masked.
