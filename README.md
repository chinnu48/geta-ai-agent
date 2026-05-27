# Geta AI Agent

## Features

- Task input through REST API and uploaded text files
- Persistent SQLite memory and execution logs
- Duplicate task detection
- Multi-step agent workflow: task parser, memory loader, execution engine, verifier
- Background task execution with FastAPI `BackgroundTasks`
- Retry and recovery endpoints for failed or interrupted tasks
- Dockerized FastAPI service
- Gemini LLM provider configurable through environment variables

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Google Gemini API
- Docker / Docker Compose

## Setup

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Install and run locally:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run with Docker:

```powershell
docker compose up --build
```

Open the API docs:

```text
http://localhost:8000/docs
```

## Flow

1. Call `GET /api/v1/health`.
2. Create a task with `POST /api/v1/tasks`.
3. View all tasks with `GET /api/v1/tasks`.
4. Inspect reasoning traces with `GET /api/v1/tasks/{task_id}/logs`.
5. View persistent memory with `GET /api/v1/memory`.
6. Retry a failed task with `POST /api/v1/tasks/{task_id}/retry`.
7. Requeue interrupted work with `POST /api/v1/tasks/recover`.

Example task body:

```json
{
  "title": "Explain Machine Learning",
  "description": "Write a clear explanation of how machine learning works, including supervised and unsupervised learning."
}
```
