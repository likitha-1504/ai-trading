# Architecture Boundaries Rule

1. **Presentation Boundary**: The React UI never executes trading logic directly; it interacts solely via FastAPI `/api/v1` endpoints.
2. **Advisory Boundary**: The AI Council (Qwen3 & DeepSeek-R1) provides advisory outputs only and cannot dispatch orders or mutate risk limits.
3. **Execution Boundary**: The Execution Engine handles order lifecycle state machines; the Position Watcher independently monitors open positions and enforces exit triggers.
4. **Persistence Boundary**: Database transactions use SQLite WAL mode with ACID durability guarantees.
