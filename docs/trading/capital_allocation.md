# Capital Allocation & Micro-Capital Controls

The AI Micro-Trading Agent is engineered specifically for controlled micro-capital operation, preventing excessive drawdown while validating real-world execution.

---

## 1. Staged Capital Progression

| Stage | Mode | Capital Ceiling | Max Risk / Trade | Prerequisites for Transition |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Paper Trading** | Simulation | ₹10,000 (virtual) | 1.5% (₹150) | 100+ simulated trades, positive expectancy, < 5% max drawdown |
| **Stage 2: Live Experiment** | Real Capital | ₹100.00 (hard cap) | 1.5% (₹1.50) | Full preflight pass (14/14), manual operator sign-off |
| **Stage 3: Autonomous Mode** | Autonomous | ₹300.00 (hard cap) | 1.5% (₹4.50) | 20+ live trades with positive net P/L after friction, user authorization |
| **Stage 4: Post-V1 Scaling** | Future Phases | User Approved | Configurable | Formal review, ADR recording, risk circuit recalibration |

---

## 2. Micro-Capital Friction Realities

Operating with small capital (₹100 to ₹300) introduces unique market realities:
- **Broker Minimum Fees**: Flat brokerage fees (e.g., ₹20 per trade) would instantly eradicate micro-capital. Therefore, the system is designed for zero-brokerage intraday brokers or operates under paper trading until capital scales.
- **Statutory Fixed Overheads**: Stamp duty, exchange fees, and GST apply to turnover. The system models these costs precisely down to 4 decimal places.
- **Lot Sizing Granularity**: Because fractional shares do not exist on the NSE/BSE, high-priced stocks (e.g., MRF, TCS) cannot be traded with ₹100. The scanner filters specifically for liquid instruments with share prices allowing 1-5 share sizing within the 1.5% risk limit.

---

## 3. Human Authorization for Capital Expansion

Any attempt to increase capital beyond the hardcoded threshold without human authorization triggers:
- HTTP 403 Forbidden on the API.
- Event logging to `system_audit_logs`.
- Hard stop rejection in `LiveExperimentEngine` and `AutonomousModeManager`.
