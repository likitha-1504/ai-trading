---
name: trading-safety-review
description: Review trading safety, deterministic risk ownership, emergency exits, broker reconciliation, and no-LLM safety-critical dependencies.
---

# Trading Safety Review Skill

This skill provides verification procedures for trading-critical operations in `ai-agent-trading`.

## Principles
1. **Deterministic Risk Ownership**: All stop losses, profit targets, risk sizing, and drawdown breakers are strictly deterministic.
2. **Zero-LLM Exit Dependency**: The Position Watcher must never rely on LLM inference or external API calls for exit logic.
3. **Emergency Exits**: Fast-path exits must execute in sub-50ms SLA.
4. **Broker Reconciliation**: The system must verify local position state against remote broker positions on startup and reconnection.
