from fastapi import FastAPI
from app.database import engine, Base
from app.routes.tasks import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Geta AI Agent",
    description="AI Agent Memory & Task Execution Platform",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "Geta AI Agent is running",
        "status": "healthy",
        "endpoints": {
            "create_task": "POST /api/v1/tasks",
            "upload_task": "POST /api/v1/tasks/upload",
            "get_all_tasks": "GET /api/v1/tasks",
            "get_task": "GET /api/v1/tasks/{task_id}",
            "get_logs": "GET /api/v1/tasks/{task_id}/logs",
            "get_memory": "GET /api/v1/memory"
        }
    }