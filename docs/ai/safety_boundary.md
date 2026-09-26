# AI Safety Boundary & Non-Override Guarantees

A central premise of the AI Micro-Trading Agent is that **large language models are non-deterministic, generative, and prone to hallucination**. Therefore, the architecture strictly segregates AI deliberation behind an unbreachable deterministic boundary.

---

## 1. Architectural Boundary Map

```
+-----------------------------------------------------------------+
|                       PROBABILISTIC PLANE                       |
|  - Qwen3 Analyst (Hypothesis & Catalyst Generation)             |
|  - DeepSeek-R1 Challenger (Adversarial Stress Testing)          |
|  - Arbitration Consensus (Consensus Scoring)                   |
+-----------------------------------------------------------------+
                                |
                                | Advisory TradePlan Artifact Only
                                v
+=================================================================+
|                      DETERMINISTIC BOUNDARY                     |
+=================================================================+
                                |
                                v
+-----------------------------------------------------------------+
|                       DETERMINISTIC PLANE                       |
|  - Deterministic Trade Gate (Hard 1.5% Risk, 3% Loss Circuit)   |
|  - Position Sizing & Statutory Cost Engine (Exact Decimal Math) |
|  - Position Watcher Thread (Sub-50ms SLA, Hard Stops, 15:15 IST)|
|  - Emergency Kill Switch (Manual Operator Control)              |
|  - Broker Adapter (Paper / Live Isolation)                      |
+-----------------------------------------------------------------+
```

---

## 2. Inviolable Safety Guarantees

1. **AI Output Is Filtered, Never Executed Directly**:
   - The AI Council cannot generate raw broker order packets.
   - It outputs only a `TradePlan` proposal containing advisory text and a score.
2. **Trade Gate Overrules All AI Models**:
   - Even if both Qwen3 and DeepSeek-R1 return 100% confidence, if the candidate violates any deterministic rule (e.g., daily drawdown >= 3.0%, time >= 15:00 IST, risk > 1.5%), the Trade Gate rejects the trade instantly.
3. **Position Watcher Operates Completely Independent of AI**:
   - Once a trade is opened, the Position Watcher thread monitors price ticks and triggers exits based strictly on mathematical stop/target prices.
   - The AI Council is **never invoked during position monitoring or exit decisions**.
4. **Graceful Failure on Model Outage**:
   - If Ollama is offline, times out, throws an Out-Of-Memory error, or returns corrupted text, the system defaults to `REJECT_TRADE`. Model failure can never result in an erroneous market entry.
