---
name: architecture-review
description: Compare changes with ARCHITECTURE.md, API contracts, schema, and trading rules.
---

# Architecture Review Skill

This skill governs architectural conformance checks for `ai-agent-trading`.

## Principles
1. **Three-Tier Boundary Check**: Ensure presentation, control plane, and watchdog execution tiers remain cleanly isolated.
2. **Contract Conformance**: Ensure API and inter-service communications adhere to `backend/app/models/contracts.py`.
3. **Database Schema Integrity**: Verify migrations and schema updates match `DATABASE_SCHEMA.md`.
4. **Trading Rule Preservation**: Verify that 1.5% trade risk, 3.0% daily drawdown stop, and 15:15 IST cutoff remain uncompromised.
