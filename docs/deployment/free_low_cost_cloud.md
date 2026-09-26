# Free & Low-Cost Cloud Deployment Guide

This guide evaluates hosting options for the AI Micro-Trading Agent on free and low-cost infrastructure, including Oracle Cloud Always Free, AWS EC2 t4g.small / Lightsail, and PaaS containers (Render, Railway, Fly.io).

---

> [!CAUTION]
> ### SAFETY-CRITICAL LIVE TRADING WARNING
> **Safety-critical live trading must NEVER depend on an unreliable, sleeping, or ephemeral free-tier cloud service.**
>
> If a hosting provider throttles your CPU, terminates your instance due to idle inactivity, sleeps your container after 15 minutes of quiet HTTP traffic, or delays outbound WebSocket packets, **your Position Watcher cannot guarantee its sub-50ms stop-loss SLA**. 
>
> In real markets, an unscheduled sleep event or dropped socket during high volatility can cause catastrophic financial loss far exceeding any hosting savings.
>
> - **Paper Trading / Development**: Free-tier cloud instances are acceptable.
> - **Real-Money Live Trading**: Use a dedicated, non-preemptible VPS (e.g., Linode/Hetzner 4GB dedicated, AWS EC2 fixed instance, or local dedicated hardware with uninterrupted power and broadband).

---

## 1. Provider Comparison for Algorithmic Micro-Trading

| Provider & Tier | Cost | Specs | Suitability for Paper Trading | Suitability for Live Trading | Key Pitfalls / Failure Modes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Oracle Cloud Always Free** (ARM Ampere) | ₹0 / mo | 4 OCPU, 24 GB RAM | **EXCELLENT** | **CONDITIONAL** | Idle reclamation policy: Oracle reclaims instances if CPU < 20% over 7 days. Can run local 7B LLM. |
| **AWS Lightsail** (Entry VPS) | ~$3.50–$5 / mo | 1–2 GB RAM, 1 vCPU | **GOOD** | **MODERATE** | Burstable CPU credits. CPU drops to baseline if burst tokens deplete. Cannot host local LLM (use remote API or separate Ollama node). |
| **AWS EC2 Free Tier** (t2.micro / t3.micro) | ₹0 for 12 mos | 1 vCPU, 1 GB RAM | **MODERATE** | **POOR** | CPU credit starvation halts processes under load. Out-of-memory crashes if Python buffers spike. |
| **Render / Railway / Fly.io** (Free tiers) | ₹0 / mo | 512 MB RAM, Shared CPU | **POOR** | **PROHIBITED** | Containers automatically go to sleep after 15 minutes of inactivity; ephemeral file storage wipes SQLite database on restart! |
| **Local Dedicated Mini-PC** (Intel N100 / AMD 5600G) | One-time ₹15k | 16–32 GB RAM, SSD | **SUPERIOR** | **SUPERIOR** | Zero recurring spend, 100% SLA control, local Ollama execution with zero latency, full SQLite NVMe throughput. |

---

## 2. Free-Tier Cloud Limitations & Architectural Hazards

### A. Automatic Sleep & Container Idling
- **The Hazard**: Free PaaS providers (e.g., Render, Glitch) detect HTTP web server silence and spin down the process to 0 replicas.
- **Trading Consequence**: The application halts. Position Watcher stops listening to market ticks. Stop-loss orders are not sent. If price plunges, open positions are unprotected until exchange auto-square-off or broker margin calls liquidate you at maximum loss.

### B. Ephemeral Disk & SQLite Destruction
- **The Hazard**: Free container tiers do not provide persistent block storage. When the container restarts or migrates, the local filesystem is recreated from git.
- **Trading Consequence**: The SQLite WAL database (`trading_agent.db`) is wiped. Active positions, running capital ledgers, and order states are completely lost on reboot.

### C. CPU Throttling & Steal Time
- **The Hazard**: "Burstable" micro-instances (AWS `t2.micro`, GCP `e2-micro`) allow brief bursts of processing. When credit balances deplete, the hypervisor severely throttles CPU execution (down to 10%–20% of one core) or introduces "CPU Steal".
- **Trading Consequence**: Position Watcher loop latency spikes from 15 microseconds to several seconds, violating the sub-50ms SLA and causing severe exit slippage.

### D. Out-of-Memory (OOM) Kills
- **The Hazard**: Running Python FastAPI, pandas, numpy, and WebSocket buffers on 512MB or 1GB RAM instances risks triggering the Linux OOM Killer.
- **Trading Consequence**: The OS abruptly terminates `python` without running cleanup handlers or flush routines, corrupting the uncommitted WAL index.

---

## 3. Recommended Low-Cost Setup: Oracle Cloud Always Free (ARM Ampere)

If you require remote cloud hosting at ₹0 spend, Oracle's Ampere A1 Compute provides up to 4 cores and 24GB RAM with persistent block storage:

### Step 1: Provisioning
1. Select **VM.Standard.A1.Flex** (4 OCPU, 24 GB RAM, Canonical Ubuntu 22.04 LTS aarch64).
2. Attach a 50 GB Boot Volume (persistent block storage).
3. Assign an Elastic Public IP.

### Step 2: Prevent Idle Instance Reclamation
Oracle automatically reclaims instances whose 7-day average CPU utilization is below 20%. To maintain an active trading node safely:
- Run scheduled strategy backtesting, health verification cron jobs, or lightweight Ollama model quantizations.
- **Never** use artificial CPU stress loops that spike latency during market hours (09:15–15:30 IST).

### Step 3: Hardening Cloud Configuration
```bash
# Update and install system dependencies
sudo apt update && sudo apt install -y python3-pip python3-venv git curl htop

# Clone repo and set up environment
git clone <repository-url> ai-agent-trading
cd ai-agent-trading
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-pinned.txt

# Configure systemd persistent service
sudo cp docs/deployment/trading-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trading-agent
```

### Step 4: Backup Cloud Database Off-Site
Because free-tier instances may be subject to provider account suspensions or datacenter maintenance, configure automated off-site backups:
```bash
# Add cron to sync backups to external S3 / B2 storage
crontab -e
# 0 16 * * 1-5 /home/ubuntu/ai-agent-trading/backend/scripts/sync_backups.sh
```
