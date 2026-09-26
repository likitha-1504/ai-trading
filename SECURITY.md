# Security Policy

## Reporting Security Issues

We take the security and integrity of algorithmic trading systems very seriously. If you discover a security vulnerability or safety-critical defect in this repository, please do not open a public issue.

Instead, please email **likithajagannadham@gmail.com** with details of the vulnerability. We will acknowledge receipt within 24 hours and provide an estimated timeline for remediation.

---

## Security Philosophy & Core Tenets

1. **Zero Secret Storage in Code**:
   - Broker credentials, API keys, private tokens, and environment configs must NEVER be committed to Git.
   - All sensitive configs are loaded via environment variables (`.env` file) which is strictly excluded via `.gitignore`.
   - Logging components employ automatic regex-based masking for sensitive keys and tokens.

2. **Deterministic Risk Isolation**:
   - Machine Learning and Large Language Model (LLM) components are strictly segregated to advisory roles.
   - The **Trade Gate** and **Position Watcher** are 100% deterministic, running in dedicated threads without any LLM dependencies or blocking network operations.
   - No AI model output can alter hard risk caps, stop losses, or daily loss limits.

3. **Guarded API Mutations**:
   - Unrestricted order placement (`POST /orders`) is permanently blocked (HTTP 405 Method Not Allowed).
   - All state mutations require valid execution tokens, operator sign-offs, or deterministic TradePlan artifacts.
   - Emergency kill-switch commands require dual-confirmation and authorization tokens.

4. **Default Paper Broker Quarantine**:
   - The default operational mode is `IS_PAPER_TRADING = True`.
   - Live trading requires multi-stage configuration override, preflight validation passing 14/14 checks, and explicit manual confirmation.

5. **Safe Database Management**:
   - SQLite WAL (Write-Ahead Logging) mode provides ACID compliance and hot online backups.
   - Hot backups are stored in a dedicated `backups/` directory (git-ignored) with cryptographic SHA-256 integrity verification.
