# Build Instructions

## Prerequisites
- **Runtime**: Python 3.11+
- **Build/Run Tooling**: pip; Docker + Docker Compose (for containerized run)
- **Dependencies**: see `requirements.txt` (FastAPI, uvicorn, SQLAlchemy, psycopg2-binary, pydantic, PyJWT, pyotp; pytest, hypothesis, httpx for tests)
- **Environment Variables**:
  - `DATABASE_URL` (e.g., `postgresql+psycopg2://portal:portal@localhost:5432/portal`)
  - `AUTH_SIGNING_SECRET` (set a real value even for the PoC)
  - Optional: `APP_ROLE` (api|worker|both, default both), `POLL_INTERVAL_MS`, `JOB_MAX_ATTEMPTS`, `RETRY_BACKOFF_CAP_MS`, `TOKEN_TTL_MINUTES`, `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_THROTTLE_SECONDS`, `LOG_LEVEL`
- **System Requirements**: any OS with Python 3.11+ / Docker; ~1GB free disk

## Build Steps

### Option A — Local (Python)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  *nix: source .venv/bin/activate
pip install -r requirements.txt
```

### Option B — Containers
```bash
docker compose build
```

### Run

Local (requires a running Postgres and the migrations applied):
```bash
# apply migrations (psql) then:
uvicorn src.app.main:app --host 0.0.0.0 --port 8000
```

Containers (starts postgres + 2 app replicas + nginx; migrations auto-applied):
```bash
docker compose up --build
# API via proxy at http://localhost:8080
```

### Verify Build/Run Success
- App logs (JSON) show "app started".
- `GET http://localhost:8080/livez` -> `{"status":"ok"}`
- `GET http://localhost:8080/readyz` -> `{"status":"ready"}` once Postgres is reachable.

## Troubleshooting
- **psycopg2 build errors**: use the provided `psycopg2-binary` (already pinned).
- **readyz 503**: Postgres not reachable / migrations not applied — check `DATABASE_URL` and that `migrations/*.sql` ran.
- **401 on protected endpoints**: obtain a token via `POST /auth/login` (seed users: admin/admin123, client/client123) and send `Authorization: Bearer <token>`.
