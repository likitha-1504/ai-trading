# Local Bare-Metal Deployment Guide

This guide describes how to run the AI Micro-Trading Agent on local commodity hardware (Windows 10/11, Linux, or macOS).

---

## 1. Prerequisites

- **Python**: Version 3.11.x (Python 3.12+ acceptable, 3.11 tested).
- **Node.js**: Version 18.x or 20.x LTS (with `npm`).
- **Ollama**: Local Ollama runtime installed and listening on `http://localhost:11434`.
  - Pulled models: `ollama pull qwen2.5:7b` (or qwen3) and `ollama pull deepseek-r1:7b` (or 8b).
- **Git**: Installed and configured.

---

## 2. Step-by-Step Installation

### Step A: Clone & Set Up Python Virtual Environment
```bash
# Clone the repository
git clone <repository-url>
cd project

# Create isolated Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Upgrade pip and install pinned production dependencies
pip install --upgrade pip
pip install -r backend/requirements-pinned.txt
```

### Step B: Environment Configuration
Create a `.env` file in the root directory:
```ini
PROJECT_NAME="AI Micro-Trading Agent"
VERSION="1.0.0"
ENVIRONMENT="production"
DATABASE_PATH="trading_agent.db"
INITIAL_CAPITAL=100.0
AUTONOMOUS_CAPITAL_THRESHOLD=300.0
IS_PAPER_TRADING=True

# Ollama Dual-LLM Configuration
OLLAMA_BASE_URL="http://localhost:11434"
QWEN_MODEL_NAME="qwen2.5:7b"
DEEPSEEK_MODEL_NAME="deepseek-r1:7b"

# Operator Security Tokens (Change to secure random values)
OPERATOR_APPROVAL_KEY="LOCAL_DEV_OPERATOR_KEY_SAFE_2026"
KILL_SWITCH_TOKEN="LOCAL_DEV_KILL_TOKEN_SAFE_2026"
```

### Step C: Run Operational Preflight Audit
Before launching, verify all 14 operational dimensions:
```bash
python backend/scripts/preflight_check.py
```
Expected output:
```
==================================================================
PHASE 23 PRODUCTION HARDENING PREFLIGHT AUDIT
Status: ALL PASSED (14/14)
Warnings: 0, Failures: 0
==================================================================
```

### Step D: Build & Launch Frontend Dashboard
```bash
cd frontend
npm install
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

### Step E: Launch Backend API & Position Watcher
In a second terminal window (with `.venv` active):
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Access the UI dashboard at: `http://localhost:5173`  
Access API documentation at: `http://localhost:8000/api/v1/docs`
