# AI Micro-Trading Agent

A local-first algorithmic micro-trading system built with Python, FastAPI, SQLite WAL, React, and local dual-LLM qualitative reasoning (Qwen3 & DeepSeek-R1).

## Architecture Principles
- **₹0 Development Spend**: Purely local software and open-source models.
- **Deterministic Risk Core**: Risk management, order execution, and stop losses are 100% deterministic and never depend on LLM inferences.
- **Independent Position Watcher**: Autonomous watchdog module that protects capital and executes emergency exits instantly.
- **Dual AI Council**: Qwen3 proposes hypotheses; DeepSeek-R1 stress-tests and critiques setups.
- **Strict Visual Segregation**: UI clearly distinguishes deterministic system facts from probabilistic AI hypotheses.

## Control Plane Documentation
- [ARCHITECTURE.md](file:///C:/Users/likit/Desktop/project/ARCHITECTURE.md)
- [PROJECT_SPEC.md](file:///C:/Users/likit/Desktop/project/PROJECT_SPEC.md)
- [DEVELOPMENT_PLAN.md](file:///C:/Users/likit/Desktop/project/DEVELOPMENT_PLAN.md)
- [TASKS.md](file:///C:/Users/likit/Desktop/project/TASKS.md)
- [DECISIONS.md](file:///C:/Users/likit/Desktop/project/DECISIONS.md)
- [CODING_RULES.md](file:///C:/Users/likit/Desktop/project/CODING_RULES.md)
- [TEST_PLAN.md](file:///C:/Users/likit/Desktop/project/TEST_PLAN.md)
- [DATABASE_SCHEMA.md](file:///C:/Users/likit/Desktop/project/DATABASE_SCHEMA.md)
- [API_CONTRACTS.md](file:///C:/Users/likit/Desktop/project/API_CONTRACTS.md)
- [TRADING_RULES.md](file:///C:/Users/likit/Desktop/project/TRADING_RULES.md)
- [FAILURE_HANDLING.md](file:///C:/Users/likit/Desktop/project/FAILURE_HANDLING.md)
- [BROKER_ADAPTER_SPEC.md](file:///C:/Users/likit/Desktop/project/BROKER_ADAPTER_SPEC.md)
- [UI_UX_SPEC.md](file:///C:/Users/likit/Desktop/project/UI_UX_SPEC.md)
- [AI_ROLES.md](file:///C:/Users/likit/Desktop/project/AI_ROLES.md)

## Repository Structure
```
project/
├── backend/
│   ├── app/
│   │   ├── adapters/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── engine/
│   │   ├── models/
│   │   ├── strategies/
│   │   ├── watcher/
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
└── [Control Plane Specifications...]
```
