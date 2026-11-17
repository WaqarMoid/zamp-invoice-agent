# 11 · GitHub, Render (backend), Vercel (frontend), Neon (database)

Read in: **Phase 8**. Steps marked **[HUMAN]** need Waqar to click in a browser or paste a secret; the agent stops, prints exact instructions, and waits. Never print or commit secrets.

## 11.1 GitHub
- Repo: `https://github.com/WaqarMoid/zamp-invoice-agent` (public, so reviewers can read the code).
- `.gitignore` (root): `.env`, `*.env.local`, `backend/.venv/`, `backend/data/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `frontend/dist/`, `.DS_Store`, `.vercel/`. **Do commit** `backend/fixtures/` and `backend/reports/`.
- If `git` is not initialised (Phase 0 should have done it): `git init -b main`.
- Check auth: `gh auth status`. If not logged in → **[HUMAN]** run `gh auth login` (GitHub.com, HTTPS, browser) and confirm.
- Create and push: `gh repo create WaqarMoid/zamp-invoice-agent --public --source . --remote origin --push --description "Invoice to decision: AP automation with a live pipeline view"`.
  If `gh` is unavailable: **[HUMAN]** create the empty repo on github.com, then `git remote add origin https://github.com/WaqarMoid/zamp-invoice-agent.git && git push -u origin main`.
- After every later phase: `git push`.

## 11.2 Neon Postgres **[HUMAN]**
1. Sign in at neon.tech with GitHub → New project `zamp-invoice-agent`, region **AWS Asia Pacific (Singapore)**, Postgres 16.
2. Copy the **pooled** connection string (`postgresql://...-pooler...?sslmode=require`). Give it to the agent only by putting it into Render's env var UI (11.3), not into chat or files.
The app creates tables and seeds on first boot.

## 11.3 Render (backend)
`render.yaml` at repo root (agent writes this):
```yaml
services:
  - type: web
    name: zamp-invoice-agent-api
    runtime: python
    plan: free
    region: singapore
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers
    healthCheckPath: /api/health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.7
      - key: DATABASE_URL
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODEL
        value: gemini-2.5-flash
      - key: LLM_PROVIDER
        value: gemini
      - key: EXTRACTION_CACHE
        value: "true"
      - key: DEMO_MODE
        value: "true"
      - key: ALLOWED_ORIGINS
        sync: false
```
(Update `GEMINI_MODEL` to the ID chosen in Phase 3.)
**[HUMAN]** steps:
1. render.com → sign in with GitHub → **New → Blueprint** → select `WaqarMoid/zamp-invoice-agent` → Apply.
2. Fill secrets when prompted: `DATABASE_URL` (Neon), `GEMINI_API_KEY` (from aistudio.google.com → Get API key), `ALLOWED_ORIGINS` = `http://localhost:5173` for now.
3. Wait for deploy; open `https://<service>.onrender.com/api/health` → `{"status":"ok",...}`. Paste the base URL to the agent.
Free tier sleeps after ~15 min idle; first request takes ~30-60 s. The UI handles this (nav status "Waking server").

## 11.4 Vercel (frontend)
`frontend/vercel.json`:
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```
**[HUMAN]** steps:
1. vercel.com → sign in with GitHub → **Add New → Project** → import `zamp-invoice-agent`.
2. Root Directory: `frontend`. Framework preset: Vite. Build `npm run build`, output `dist` (defaults).
3. Environment variable `VITE_API_BASE_URL` = the Render URL (no trailing slash). Deploy.
4. Copy the production URL (e.g. `https://zamp-invoice-agent.vercel.app`).
5. Back in Render → Environment → set `ALLOWED_ORIGINS` = `https://zamp-invoice-agent.vercel.app,http://localhost:5173` → save (auto-redeploys).
Vercel and Render both auto-deploy on every push to `main` from now on.

## 11.5 Production verification (agent, after URLs exist)
1. `curl {RENDER}/api/health`.
2. Open the Vercel URL; nav shows "Live".
3. Rules page → Reset demo data.
4. Run F01-F05 from the UI; confirm decisions match doc 07 §7.9. Run F03 with cache **off** once to prove live vision extraction works in prod.
5. Check SSE works through Render (stages animate live, not all at once). If events arrive in one burst, confirm `X-Accel-Buffering: no` header and that responses are not gzip-compressed for `text/event-stream`.
6. Reset demo data again so the reviewer starts clean.
7. Write both URLs at the top of README.md and in PROGRESS.md.

## 11.6 Keep-warm (optional, before demo/interview)
Open the app 2 minutes before recording or the interview. Do not add an external cron pinger unless Waqar asks.
