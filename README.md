# Blackbird QA Backend

A FastAPI-based backend service for managing and processing User Stories (HUs) and test cases, integrating with Azure DevOps and AI services.

## Features

- Fetch and manage User Stories from Azure DevOps
- AI-powered refinement of User Stories
- Generate test cases in XRay format
- Track HU status and feedback
- Debug endpoints for development

## Prerequisites

- Python 3.13+
- Docker (optional, for containerized deployment)
- Azure DevOps account with appropriate permissions
- DeepSeek API key

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Azure DevOps
AZURE_ORGANIZATION=your_org
AZURE_PROJECT=your_project
AZURE_PAT=your_personal_access_token

# DeepSeek AI
DEEPSEEK_API_KEY=your_deepseek_api_key

# Database (SQLite by default)
DATABASE_URL=sqlite:///./test.db
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd riwi_qa_backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, you can access:

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Alternative API docs: `http://127.0.0.1:8000/redoc`

## API Endpoints

### User Stories (HUs)

#### Create a new HU
- **POST** `/api/hus/`
  - Creates a new User Story by fetching data from Azure DevOps and refining it with AI
  - Request body: `{ "azure_id": "12345" }`

#### List all HUs
- **GET** `/api/hus/`
  - Query parameters:
    - `status`: Filter by status (optional)
    - `feature`: Filter by feature (optional)
    - `module`: Filter by module (optional)

#### Get HU by ID
- **GET** `/api/hus/{hu_id}`
  - Returns the details of a specific User Story

#### Update HU Status
- **PATCH** `/api/hus/{hu_id}/status`
  - Updates the status of a User Story
  - Request body: `{ "status": "approved", "feedback": "Optional feedback" }`

### Test Generation

#### Generate and Send Tests
- **POST** `/api/tests/generate`
  - Generates test cases for a User Story and sends them to XRay
  - Request body: 
    ```json
    {
        "xray_path": "path/to/xray/export.json",
        "azure_id": "12345"
    }
    ```

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
