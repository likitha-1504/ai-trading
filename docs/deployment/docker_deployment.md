# Docker Deployment Guide

The AI Micro-Trading Agent includes a production-ready, multi-stage Docker build and compose orchestration setup.

---

## 1. Container Architecture

The system utilizes a lightweight, multi-stage Debian/Alpine build:
1. **Frontend Stage**: Node 20 LTS compiles TypeScript and bundles Vite production assets into static files.
2. **Backend Runtime**: Python 3.11 slim runtime hosting FastAPI, SQLite WAL persistence, and static asset serving.
3. **Data Volume**: Named persistent volume `trading_agent_data` to ensure the SQLite WAL database and backup snapshots survive container restarts.

---

## 2. Docker Compose Setup

Run the application stack using Docker Compose:

```bash
# Build and start in detached mode
docker-compose up --build -d

# Inspect running container logs
docker-compose logs -f

# Verify container health
docker-compose ps
```

### Docker Compose Service Definition Summary

```yaml
version: '3.8'

services:
  trading-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ai_micro_trading_agent
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - IS_PAPER_TRADING=true
      - INITIAL_CAPITAL=100.0
      - DATABASE_PATH=/data/trading_agent.db
    volumes:
      - trading_agent_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/system/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  trading_agent_data:
    driver: local
```

---

## 3. Database Backups from Container

To trigger an online SQLite hot backup from inside the running container:

```bash
docker exec -it ai_micro_trading_agent python backend/scripts/backup.py --reason scheduled_hot_backup
```

To list available verified backups:
```bash
docker exec -it ai_micro_trading_agent python -c "from app.ops.backup_manager import BackupManager; print(BackupManager().list_backups())"
```
