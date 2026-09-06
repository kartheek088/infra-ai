# Inferago — Multi-Platform AI Workflow Monitor

Token usage monitoring, RAG analytics, and optimization suggestions
for n8n, Make, Zapier, and any custom automation platform.

## Stack
- **Backend**: FastAPI + PostgreSQL + Redis
- **Frontend**: React + Vite + TypeScript + Tailwind
- **Auth**: JWT + API Keys
- **ORM**: SQLAlchemy + Alembic

## Supported Platforms
- n8n
- Make (Integromat)
- Zapier
- Custom (any platform via universal webhook)

## Quick Start

### 1. Start Docker
```bash
docker-compose up -d
```

### 2. Backend
```bash
cd backend
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```
Visit: http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit: http://localhost:5173

## Webhook Setup (per platform)

### n8n
```
Settings → Workflow → On Execution End
URL: https://your-inferago.com/api/webhook/n8n?api_key=YOUR_KEY
```

### Make
```
Scenario → Settings → Webhook → On Completion
URL: https://your-inferago.com/api/webhook/make?api_key=YOUR_KEY
```

### Zapier
```
Add "Webhooks by Zapier" step at end of Zap
URL: https://your-inferago.com/api/webhook/zapier?api_key=YOUR_KEY
```

### Custom
```
POST https://your-inferago.com/api/webhook/custom?api_key=YOUR_KEY
Send our standard JSON format (see /docs)
```

## Project Structure
```
inferago_complete/
├── docker-compose.yml
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── alembic/
│   └── app/
│       ├── main.py
│       ├── adapters/      ← platform adapters
│       ├── core/          ← config, security, deps
│       ├── db/            ← engine, session
│       ├── middleware/    ← error handler, rate limiter
│       ├── models/        ← SQLAlchemy tables
│       ├── schemas/       ← Pydantic shapes
│       ├── routers/       ← API endpoints
│       └── services/      ← business logic
└── frontend/
    └── src/
        ├── api/
        ├── store/
        ├── pages/
        ├── components/
        └── hooks/
```
