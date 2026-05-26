# Architecture

## System Overview

The platform is a FastAPI service that accepts task requests, stores them in SQLite, and runs an AI agent workflow in the background. Each workflow stage writes execution logs so the system can explain what happened during task execution.

## Main Components

- `app/main.py`: FastAPI app setup, database table creation, router registration.
- `app/routes/tasks.py`: REST API for task creation, file upload, listing, logs, memory, retry, and recovery.
- `app/agent.py`: Multi-stage agent workflow and LLM calls.
- `app/database.py`: SQLAlchemy engine and session factory.
- `app/models.py`: Task, Memory, and ExecutionLog tables.

## Workflow

1. A task is submitted through `POST /api/v1/tasks` or `POST /api/v1/tasks/upload`.
2. The API checks for duplicate task descriptions.
3. The task is saved with `pending` status.
4. A background worker opens its own database session and marks the task as `running`.
5. The agent parses the task into structured objectives.
6. The memory loader retrieves relevant prior task summaries.
7. The execution engine generates the final result.
8. The verifier checks whether the result satisfies the original request.
9. The task result, memory summary, and reasoning logs are persisted.

## Reliability Decisions

- Each background task creates its own database session instead of reusing the request session.
- Failed tasks store failure reasons for debugging.
- Provider errors such as invalid API key, missing model, and quota exhaustion are treated as non-retryable.
- `POST /api/v1/tasks/{task_id}/retry` lets an operator retry a task after fixing configuration.
- `POST /api/v1/tasks/recover` requeues tasks that were left pending, running, or retrying after an interruption.
- Exact duplicate task descriptions are not executed again.

## Database Tables

- `tasks`: task metadata, status, result, retry count, and failure reason.
- `memory`: task summaries used as persistent memory.
- `execution_logs`: step-by-step reasoning trace for each task.
