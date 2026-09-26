# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-26

### General
- Official V1 Release of the AI Micro-Trading Agent.
- Zero-spend, local-first algorithmic trading system designed for Indian equities (NSE/BSE).
- Dual-engine design featuring deterministic risk enforcement and local dual-LLM advisory reasoning (Qwen3 & DeepSeek-R1).

### Added
- **Core Engine & Architecture (Phases 00–04)**:
  - Three-tier modular architecture isolating UI, Backend orchestration, and Independent Position Watcher.
  - SQLite Write-Ahead Logging (WAL) persistent store with full ACID transaction guarantees.
  - Normalized market data adapter with WebSocket streaming, tick validation, and stale feed detection.
  - High-performance feature engine calculating EMA, RSI, ATR, VWAP, and Realized Volatility with sub-millisecond latency.
  - Complete data contracts in `backend/app/models/contracts.py` with strict Pydantic validation.

- **Technical Strategies & Trade Gate (Phases 05–08)**:
  - Early Move & Momentum Continuation intraday strategies with deterministic entry/exit rules.
  - Candidate ranker scoring opportunities on liquidity, momentum, and risk-reward profile.
  - 100% Deterministic Trade Gate enforcing hard limits: 1.5% max risk per trade, 3.0% daily drawdown stop, and 15:15 IST auto-square-off.
  - Comprehensive statutory Indian cost model calculating Brokerage, STT, Exchange fees, SEBI turnover, GST, and Stamp Duty.

- **SELL Engine & Position Watcher (Phases 09–10)**:
  - Dedicated, isolated Position Watcher thread operating on sub-50ms SLA without LLM or external API dependencies.
  - Dynamic stop-loss tracking (trailing stops, ATR volatility stops, profit targets, time expiries).
  - Emergency fast-path exit triggers for abnormal volatility or feed interruptions.

- **AI Council Advisory Plane (Phases 11–13)**:
  - Dual-LLM deliberation pipeline integrating Ollama local inference.
  - **Qwen3 Analyst**: Formulates qualitative investment theses and technical opportunity assessments.
  - **DeepSeek-R1 Challenger**: Adversarially stress-tests hypotheses, identifies hidden failure modes, and issues counter-theses.
  - Algorithmic consensus scoring and arbitration matrix. Total isolation ensuring AI output cannot override deterministic safety limits.

- **FastAPI Control Plane & Dashboard UI (Phases 14–15)**:
  - Complete REST API (`/api/v1`) with 13 safe query endpoints and token-guarded mutation routes.
  - Arbitrary order placement permanently blocked (POST /orders returns 405 Method Not Allowed).
  - 15 dedicated terminal screens in React 18 / TypeScript / Tailwind CSS with strict visual segregation between deterministic facts and AI reasoning.
  - Dual-confirmation emergency kill-switch modal.

- **Testing, Verification & Failure Injection (Phases 16–19)**:
  - Comprehensive 251-test suite spanning 22 test modules with 100% pass rate.
  - Chaos engineering & failure injection: simulated network disconnects, broker timeouts, database WAL lock contention, and bad ticks.
  - Sub-50ms latency verification and benchmark profiling across all execution paths.
  - End-to-end paper trading validation engine simulating realistic order book fills and slippage.

- **Controlled Live Experimentation & Autonomous Mode (Phases 20–22)**:
  - Controlled ₹100 live experiment engine with 9-dimension telemetry monitor.
  - Controlled ₹300 autonomous mode with multi-tier risk controls and human approval gates.
  - 8-dimension post-trade learning analytics loop generating versioned strategy improvement proposals without automatic deployment.

- **Production Hardening & Operations (Phases 23–24)**:
  - Automated SQLite WAL online hot backups with SHA-256 integrity verification and rotation.
  - Multi-tier system health probes monitoring DB WAL, disk space, backup freshness, Watcher SLA, broker connectivity, and AI Council.
  - 14-dimension operational preflight audit runner (`backend/scripts/preflight_check.py`).
  - Comprehensive operational manuals (`RUNBOOK.md`, `OPERATIONS.md`, `INCIDENT_RESPONSE.md`, `BACKUP_RECOVERY.md`, `RELEASE_CHECKLIST.md`).
  - Pinned production requirements (`backend/requirements-pinned.txt`) and container deployment manifests (`Dockerfile`, `docker-compose.yml`).
