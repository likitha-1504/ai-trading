# Trading Safety Rule

1. **Deterministic Risk Supremacy**:
   - The Trade Gate and Position Watcher are 100% deterministic and isolated from LLMs.
   - Stop loss orders, sizing, drawdown caps, and cutoff times must never depend on model outputs or network calls.
2. **Sub-50ms SLA**:
   - Position Watcher evaluation hot-path must execute within sub-50ms.
   - Zero blocking disk I/O or network requests allowed during price tick evaluation.
3. **No Live Trading During Development**:
   - `IS_PAPER_TRADING` must default to `True`.
   - Live trading requires explicit user approval and a clean 14/14 preflight audit.
