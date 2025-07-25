# Blackbird QA Backend – Developer Guide

_Last updated: 2025-07-25_

This guide documents the internal architecture, code conventions, and extension points of the **Blackbird QA Backend**. It complements the end-user `README.md` by focusing on details required to maintain and extend the codebase.

---

## 1. Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Web framework | FastAPI | 0.104.1 |
| ASGI server | Uvicorn (standard extras) | 0.24.0 |
| ORM | SQLAlchemy 2 (declarative) | 2.0.23 |
| Validation | Pydantic v2 | 2.5.0 |
| Auth | OAuth2 (JWT via `python-jose`) | 3.3.0 |
| DB | SQLite (default) / any SQLAlchemy URL | — |
| External APIs | Azure DevOps REST, DeepSeek-AI, XRay | — |

Python 3.11+ is recommended; the project was last tested on 3.13.

---

## 2. Repository Layout

```
riwi_qa_backend/
├── app/                  # FastAPI application package
│   ├── __init__.py
│   ├── main.py           # app entry-point (routes wired here)
│   ├── api/              # High-level business endpoints
│   │   └── routes.py
│   ├── auth/             # AuthN/AuthZ helpers & routes
│   │   ├── jwt.py        # token creation & validation
│   │   └── routes.py
│   ├── database/
│   │   └── connection.py # SQLAlchemy engine/session
│   ├── middleware/       # (placeholder for future cross-cutting concerns)
│   ├── schemas/          # Pydantic models (request/response)
│   │   └── hu_schemas.py
│   ├── services/         # Integration/adaptor layer
│   │   ├── azure_service.py
│   │   ├── deepseek_service.py
│   │   └── xray_service.py
│   └── utils/            # Misc helpers (logging, pagination, etc.)
├── run.py                # optional script → executes uvicorn
├── requirements.txt
├── .env.example
└── README.md / DEVELOPER_GUIDE.md
```

---

## 3. Application Flow

1. **Auth** – Clients request a JWT at `POST /auth/token`. In dev mode the in-memory `fake_users_db` accepts `test` / `test123`.
2. **HU Creation** – `POST /hus` receives `HUCreate` with an `azure_id`:
   a. `services.azure_service.AzureService` fetches work-item JSON via Azure DevOps REST.
   b. `services.deepseek_service.DeepSeekService` refines the description to produce `refined_response` & `markdown_response`.
   c. The HU is persisted via SQLAlchemy and returned to the caller.
3. **HU Inspection** – `GET /hus` & `GET /hus/{id}` expose filtered reads.
4. **Status Update** – `PATCH /hus/{id}/status` writes approval / feedback.
5. **Test Generation** – `POST /generate-tests` triggers the DeepSeek prompt → generates XRay JSON → `services.xray_service.XRayService` uploads (or stores locally if mocked).

All write endpoints require valid JWT.

---

## 4. Database Schema

The ORM model lives under `app/database/models.py` (to be created once migrations are introduced). Currently, `HU` is defined ad-hoc inside services; Alembic support is scaffolded but unused.

Key fields:
* `id` – UUID-v4 PK
* `azure_id` – Work item ID (unique)
* `name`, `description`
* `status` – enum: _pending_, _approved_, _rejected_
* `refined_response`, `markdown_response`
* `feature`, `module`
* timestamps: `created_at`, `updated_at`

---

## 5. Service Layer Details

### 5.1 AzureService
`services/azure_service.py`
* Builds base64 PAT auth header.
* `get_work_item(azure_id)` fetches selective fields to minimize payload.
* Caches responses for 15 minutes (in-memory `functools.lru_cache`).
* Raises `HTTPException(404)` when not found.

### 5.2 DeepSeekService
* Wraps calls to the DeepSeek completion endpoint.
* Prompt templates live at top of the file → tweak carefully (affects AI cost).
* Timeout default: 60 s (via `requests`).
* Errors bubble up as 502.

### 5.3 XRayService
* Converts refined HU into XRay JSON schema.
* `send_to_xray(json_path)` makes multipart POST to XRay cloud.
* In dev mode (`XRAY_BASE_URL` absent) the payload is written to `./xray_exports/`.

---

## 6. Error Handling Strategy

* All exceptions ultimately map to FastAPI `HTTPException` (non-2xx return).
* Services should throw their own subclass or plain `HTTPException` – never return bare dict errors.
* Generic 422 / 400 automatically provided by FastAPI when validation fails.

---

## 7. Testing

* **Unit tests** – place under `tests/` (pytest autodiscovery). Use `pytest-asyncio` for async routes.
* **Integration** – spin up ephemeral SQLite (`DATABASE_URL=sqlite:///:memory:`) and hit routes via `httpx.AsyncClient`.
* Ensure CI runs `pytest -q` plus Ruff (or flake8) linting.

---

## 8. Extending the Project

| Task | Guidance |
|------|----------|
| Add new external system | Create a service module under `app/services/` and expose via new endpoint module under `app/api/`. Keep business logic out of `main.py`. |
| Replace SQLite → Postgres | Update `.env` `DATABASE_URL=postgresql+psycopg://user:pass@host/db` and install `psycopg2-binary`. Run Alembic migrations. |
| Real user database | Swap `fake_users_db` for SQL-backed users table + passlib hash. Adjust `get_user()` in `auth/jwt.py`. |
| Async I/O | Services currently use `requests` (blocking). Port to `httpx.AsyncClient` if higher concurrency required. |

---

## 9. Deployment Notes

* **Docker** image uses Python slim; multi-stage build suggested for smaller size.
* Ensure `JWT_SECRET_KEY` is strong and not committed.
* Add a reverse proxy (nginx / Traefik) to terminate TLS and forward to Uvicorn workers (Gunicorn with `uvicorn.workers.UvicornWorker` for multi-process scale).
* Configure health probe at `/health` for orchestrators (K8s, ECS, etc.).

---

## 10. Roadmap / TODO

- [ ] Formalize SQLAlchemy models & migrations
- [ ] Replace in-memory auth with proper user DB
- [ ] Write automated contract tests for Azure & XRay integrations
- [ ] Transition to async HTTP clients
- [ ] Add rate-limit & request-ID middleware

---

Happy hacking! If anything is unclear, ping the last maintainer or open an issue.
