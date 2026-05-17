# InsightSQL — HPE GreenLake SAP Operations Copilot

> AI-driven Text-to-SQL investigation, self-healing dashboard queries, and real-time observability for HPE-managed SAP workloads.

![Dashboard](docs/dashboard.png)

## What It Does

InsightSQL is a **live operations dashboard** for HPE GreenLake-hosted SAP environments. When an incident occurs, it:

1. **Ingests telemetry** — Grafana alerts, HPE compute health events, and storage metrics via webhooks
2. **Auto-investigates** — Uses Text-to-SQL (Azure OpenAI gpt-5.4-mini) to query operational data with full schema grounding, AST validation, and read-only execution
3. **Generates RCA** — Produces ranked root-cause hypotheses with confidence scores and evidence chains
4. **Self-heals dashboards** — When a panel SQL breaks (e.g., column rename), the AI healer detects the error, generates a fix, shadow-runs it, and promotes the new version — zero downtime

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  React Dashboard (Vite)                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ KPI Cards│ │ Timeline │ │ Topology │ │ AI Chain │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Evidence │ │   RCA    │ │Panel Heal│ │Demo Ctrl │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ WebSocket + REST
┌──────────────────────┴──────────────────────────────────────────┐
│  FastAPI Backend (Python 3.12)                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Ingestion  │ │ Text2SQL   │ │ SQL Healer │ │ RCA Engine   │ │
│  │ Normalizer │ │ Agent      │ │            │ │              │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │ SQLGlot    │ │ EXPLAIN    │ │ Demo       │                  │
│  │ Validator  │ │ Executor   │ │ Scenarios  │                  │
│  └────────────┘ └────────────┘ └────────────┘                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │  PostgreSQL 16          │
          │  RHEL VM (db-host)      │
          │  11 tables, ops schema  │
          └─────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, ECharts, D3-force, Lucide icons |
| Backend | Python 3.12, FastAPI, asyncpg, SQLGlot, uv |
| AI | Azure OpenAI gpt-5.4-mini (4-deployment rotation) |
| Database | PostgreSQL 16 on RHEL 9 |
| Design | HPE Graphik fonts, custom dark-mode design system |

## Quick Start

### Prerequisites
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- PostgreSQL 16 instance

### Backend
```bash
cd backend
cp .env.example .env  # Fill in your Azure OpenAI credentials
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run Demo
Click **Run Demo** in the bottom-right corner, or:
```bash
curl -X POST http://localhost:8000/api/demo/start
```

## Demo Scenarios

| # | Incident | What Happens |
|---|----------|-------------|
| 1 | SAP Slowdown | Grafana alert → metrics spike → 2 AI investigations → RCA: backup I/O contention on HPE Primera |
| 2 | Compute Degradation | Host thermal event → temperature spike → cross-correlation → RCA update: compound root cause |
| 3 | SQL Self-Heal | Panel SQL intentionally broken → failure detected → LLM generates fix → shadow-run → auto-promoted |

## Environment Variables

```env
AZURE_OPENAI_ENDPOINT=https://oai-gopoc-prod-northcentralus-001.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-12-01-preview
DATABASE_URL=postgresql://<user>:<password>@<db-host>:5432/insightsql
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + PG version |
| GET | `/api/topology` | Infrastructure graph (nodes + edges) |
| GET | `/api/panels` | Dashboard panels with active SQL |
| POST | `/api/demo/start` | Start 3-incident demo |
| POST | `/api/demo/reset` | Reset DB and re-seed |
| WS | `/ws` | Real-time event stream |

## Team

Built for HPE Digithon 2026.
