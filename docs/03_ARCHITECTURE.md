# 03 · Architecture, stack and repository layout

Read in: **Phase 0** (all).

## 3.1 Overview
```
Browser (Vercel, React SPA)
   │  REST (JSON) + SSE (EventSource), direct to backend URL, CORS
   ▼
FastAPI on Render (1 worker, uvicorn)
   ├─ pipeline runner (asyncio task per run, global lock)
   ├─ extraction → Gemini API (only external call)
   └─ SQLAlchemy → Postgres on Neon (prod) / SQLite file (local)
```
Why these choices (say in the interview): Python for PDF tooling; FastAPI for async + SSE; deterministic rules engine in plain Python for testability; SSE (not WebSockets) because updates are one-way and SSE auto-reconnects with `Last-Event-ID`; Neon because Render's free Postgres expires and Render's free disk is ephemeral.

## 3.2 Versions (pin these)
Backend `requirements.txt`:
```
fastapi>=0.115,<1
uvicorn[standard]>=0.30
sqlalchemy>=2.0.30,<2.1
psycopg[binary]>=3.2
pydantic>=2.8,<3
pydantic-settings>=2.4
python-multipart>=0.0.9
sse-starlette>=2.1
pdfplumber>=0.11
pymupdf>=1.24
rapidfuzz>=3.9
python-dateutil>=2.9
google-genai>=1.0
pillow>=10.4
numpy>=1.26
reportlab>=4.2
pytest>=8.3
httpx>=0.27
```
Python **3.12**. Node **20 LTS**. Frontend deps: `react@18 react-dom@18 react-router-dom@6 @tanstack/react-query@5 lucide-react tailwindcss@4 @tailwindcss/vite @fontsource/raleway @fontsource/source-sans-3 @fontsource/ibm-plex-mono`; dev: `typescript vite @vitejs/plugin-react vitest @testing-library/react @playwright/test`.

## 3.3 Repository layout (this folder is the git root)
```
zamp assignment/                     → GitHub repo WaqarMoid/zamp-invoice-agent
├── AGENT_START_PROMPT.md
├── README.md                         (rewritten in Phase 8 for reviewers)
├── PROGRESS.md                       (agent's tracker; always current)
├── render.yaml
├── .gitignore
├── docs/                             (this spec)
├── skills/frontend-design/SKILL.md
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                  FastAPI app, CORS, startup (create tables, seed, mark interrupted runs)
│   │   ├── config.py                Settings (pydantic-settings), all thresholds from doc 07 §7.3
│   │   ├── db.py                    engine/session; sqlite pragma foreign_keys=ON
│   │   ├── models.py                ORM tables (doc 04 §4.2)
│   │   ├── schemas.py               Pydantic models (doc 04 §4.3-4.4) + API response models
│   │   ├── seed.py
│   │   ├── seed_data/*.json         (provided)
│   │   ├── api/                     health.py samples.py runs.py procurement.py stats.py admin.py
│   │   ├── pipeline/
│   │   │   ├── runner.py  context.py  events.py  stages_registry.py
│   │   │   └── stages/   ingest.py extract.py normalize.py vendor.py duplicates.py po_match.py reconcile.py decide.py
│   │   ├── extraction/              llm_client.py gemini.py openai_client.py prompt.py text_layer.py render.py heuristic.py
│   │   └── rules/                   money.py gstin.py text.py matching.py checks.py messages.py actions.py email_draft.py consumption.py
│   ├── scripts/                     generate_fixtures.py eval_extraction.py
│   ├── fixtures/                    F01..F09 PDFs + golden/*.json (generated, committed)
│   ├── reports/                     extraction_eval.md, golden_results.md
│   └── tests/
└── frontend/
    ├── index.html  vite.config.ts  tsconfig.json  vercel.json  .env.example
    └── src/
        ├── main.tsx  App.tsx (routes)
        ├── styles/  tokens.css  globals.css
        ├── lib/     api.ts  types.ts  format.ts  useRunStream.ts  queryClient.ts
        ├── components/  (doc 09 §9.7)
        └── pages/   Dashboard.tsx  NewRun.tsx  RunDetail.tsx  PurchaseOrders.tsx  Rules.tsx  NotFound.tsx
```

## 3.4 Environment variables
`backend/.env.example`:
```
DATABASE_URL=sqlite:///./data/app.db
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini
EXTRACTION_CACHE=true
ALLOWED_ORIGINS=http://localhost:5173
DEMO_MODE=true
LOG_LEVEL=INFO
```
Postgres URLs from Neon start with `postgresql://`; in `db.py` rewrite to `postgresql+psycopg://` and keep `?sslmode=require`. Engine: `pool_pre_ping=True`, `pool_size=5`.
`frontend/.env.example`: `VITE_API_BASE_URL=http://localhost:8000`.

## 3.5 Local run commands (document in README)
```
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python scripts/generate_fixtures.py
uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

## 3.6 Coding standards
- Type hints everywhere; `ruff` clean (add `ruff` to dev usage, config in `backend/pyproject.toml`, line length 110).
- No business logic in API route functions; routes call services.
- All user-visible strings for checks live in `rules/messages.py` (one place to edit copy).
- Logging: `logging` with run_id in every pipeline log line.
- Frontend: TypeScript strict, no `any` except at JSON boundaries, one component per file, no inline hex colours (use tokens).
- Commit after every phase and after each sub-phase of Phase 6: `git commit -m "phase N: <what>"`.
