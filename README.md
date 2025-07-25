# Blackbird QA Backend

A production-ready FastAPI service that fetches, refines, and tracks **User Stories (HUs)** from Azure DevOps and generates fully-formatted XRay test cases with the help of AI.

---

##  Key Features

• 🔗 Integrates directly with **Azure DevOps** to pull HU metadata  
• 🧠 Uses **DeepSeek-AI** to refine HU descriptions for clarity  
• 📝 Outputs ready-to-import **XRay JSON** test cases  
• 📊 Tracks HU status/feedback through an SQL database  
• 🔒 OAuth2 (JWT)–protected endpoints  
• 🛠  Debug routes for rapid inspection while developing

---

## Quick Start (Local)

```bash
# 1 — clone
$ git clone https://github.com/<your-org>/blackbird-qa-backend.git
$ cd blackbird-qa-backend/riwi_qa_backend

# 2 — prepare Python env (3.11+ recommended)
$ python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\activate

# 3 — install deps
$ pip install -r requirements.txt

# 4 — copy env template and fill credentials
$ cp .env.example .env
$ nano .env  # or favourite editor

# 5 — run dev server
$ uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| AZURE_ORGANIZATION | Azure DevOps org slug |
| AZURE_PROJECT | Azure project name |
| AZURE_PAT | Personal Access Token with **Work Items (read)** scope |
| DEEPSEEK_API_KEY | Key for DeepSeek large-language-model |
| DATABASE_URL | SQLAlchemy URL (`sqlite:///./riwi_qa.db` by default) |
| JWT_SECRET_KEY | Secret used to sign JWTs |
| CORS_ORIGINS | Comma-separated allowed origins (optional) |

Place them in `.env` or export in your runtime environment.

---

## API Overview

### Authentication Flow
1. `POST /auth/token` with form data `username` & `password` (dev default: `test` / `test123`).
2. Receive `{ "access_token": "<jwt>", "token_type": "bearer" }`.
3. Supply `Authorization: Bearer <jwt>` on subsequent requests.

### Primary Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Root health message |
| GET | /health | Liveness probe |
| POST | /hus | Pull HU from Azure and create DB record |
| GET | /hus | List HUs (`status`, `name`, `azure_id`, `feature`, `module` filters) |
| GET | /hus/{hu_id} | Retrieve single HU |
| PATCH | /hus/{hu_id}/status | Update status / feedback |
| POST | /generate-tests | Produce & send XRay tests |

### Debug (restricted)
| GET /debug/hus | Full HU dump |
| GET /debug/hu/{azure_id} | Find HU by Azure ID |

Swagger/OpenAPI docs auto-generated at `/docs` and `/redoc`.

---

## Database & Migrations

SQLite is used out-of-the-box. Swap to Postgres etc. by editing `DATABASE_URL`.

For schema evolution we recommend **Alembic**:

```bash
### Debug Endpoints

#### List All HUs (Debug)
- **GET** `/api/debug/hus`
  - Lists all HUs in the database with full details

#### Find HU by Azure ID (Debug)
- **GET** `/api/debug/hus/{azure_id}`
  - Finds an HU by its Azure DevOps ID

## Data Models

### HU (User Story)
```typescript
{
    "id": "string",
    "azure_id": "string",
    "name": "string",
    "description": "string | null",
    "status": "string",
    "refined_response": "string | null",
    "markdown_response": "string | null",
    "feature": "string | null",
    "module": "string | null",
    "created_at": "string | null",
    "updated_at": "string | null"
}
```

## Error Handling

The API returns appropriate HTTP status codes along with JSON error responses in the following format:

```json
{
    "detail": "Error message"
}
```

## Development

### Database Migrations

To create a new migration:

```bash
# Install alembic if not already installed
pip install alembic

# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head
```

### Testing

Run tests using pytest:

```bash
pytest
```

## Deployment

### Docker

Build the Docker image:

```bash
docker build -t blackbird-qa-backend .
```

Run the container:

```bash
docker run -d -p 8000:8000 --env-file .env blackbird-qa-backend
```

## License

[Specify your license here]

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
