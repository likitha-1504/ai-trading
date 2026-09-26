# Developer Getting Started Guide

Welcome to the development environment of the AI Micro-Trading Agent. Follow these instructions to set up your local development workspace, run tests, and spin up development servers.

---

## 1. System Requirements

- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS 12+
- **Python**: 3.11.x
- **Node.js**: 18.x or 20.x LTS
- **Ollama**: (Optional for pure unit tests, required for AI Council deliberation)

---

## 2. Setting Up the Python Backend

```bash
# 1. Clone the repository
git clone <repository-url>
cd project

# 2. Create the Python virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Windows:
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# 4. Install backend dependencies
pip install -r backend/requirements.txt
```

---

## 3. Running Backend Tests & Quality Checks

The repository enforces strict code quality gates:

```bash
# Run full pytest regression suite (251 items)
pytest

# Run static type checking across all 114+ source files
mypy backend/app

# Run linter
ruff check backend/

# Run the 14-dimension production hardening preflight audit
python backend/scripts/preflight_check.py
```

---

## 4. Setting Up the Frontend Dashboard

```bash
cd frontend

# Install npm dependencies
npm install

# Run Vite development server
npm run dev

# Run TypeScript compilation and production build check
npm run build
```

The frontend dashboard will be available at `http://localhost:5173`.

---

## 5. Environment Variables & Sandbox Configuration

Copy `.env.example` (or create `.env`) in the root:
```ini
PROJECT_NAME="AI Micro-Trading Agent"
VERSION="1.0.0"
ENVIRONMENT="development"
DATABASE_PATH="trading_agent.db"
INITIAL_CAPITAL=100.0
AUTONOMOUS_CAPITAL_THRESHOLD=300.0
IS_PAPER_TRADING=True
```
*Note*: During development, `IS_PAPER_TRADING` must always be `True`.
