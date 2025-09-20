# CyberScope Dashboard Backend

FastAPI backend providing threat intelligence APIs for the CyberScope dashboard. The service collects CVE data, enriches it with AI analysis, and exposes metrics for the React frontend.

## Prerequisites

- Python 3.11
- SQLite (bundled)
- OpenAI API key (optional for production quality analysis)

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your OpenAI API key and database URL if required.

## Running

```bash
uvicorn dashboard_backend.main:app --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001/api/dashboard` with a health check at `/health`.

## Testing

```bash
pytest
```

## Key Components

- **`models/`** — SQLAlchemy ORM models and Pydantic response schemas.
- **`services/threat_collector.py`** — Fetches data from NVD and other sources, schedules daily runs, and stores threats.
- **`services/llm_analyzer.py`** — Wraps OpenAI analysis with token budgeting and fallbacks.
- **`services/risk_engine.py`** — Computes risk scores and categories.
- **`api/dashboard_routes.py`** — REST endpoints with caching and filtering.

## Deployment

See `deployment/install.sh` and `deployment/cyberscope.service` for a Raspberry Pi deployment workflow using systemd and nginx.
