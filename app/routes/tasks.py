from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Task, Memory, ExecutionLog
from app.agent import run_agent

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: str


@router.post("/tasks")
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(Task).filter(Task.description == task.description).first()
    if existing:
        return {"message": "Task already exists", "task_id": existing.id, "status": existing.status}

    db_task = Task(title=task.title, description=task.description, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    background_tasks.add_task(run_agent, db_task.id, task.title, task.description)

    return {"message": "Task created and queued", "task_id": db_task.id}


@router.post("/tasks/upload")
async def upload_task_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8")

    lines = text.strip().split("\n")
    title = lines[0].strip() if lines else "Uploaded Task"
    description = text.strip()

    existing = db.query(Task).filter(Task.description == description).first()
    if existing:
        return {"message": "Task already exists", "task_id": existing.id}

    db_task = Task(title=title, description=description, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    background_tasks.add_task(run_agent, db_task.id, title, description)

    return {"message": "Task uploaded and queued", "task_id": db_task.id}


@router.get("/tasks")
def get_all_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return tasks


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/{task_id}/logs")
def get_task_logs(task_id: int, db: Session = Depends(get_db)):
    logs = db.query(ExecutionLog).filter(ExecutionLog.task_id == task_id).all()
    return logs


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "pending"
    task.retry_count = 0
    task.failure_reason = None
    db.commit()

    background_tasks.add_task(run_agent, task.id, task.title, task.description)
    return {"message": "Task re-queued", "task_id": task.id}


@router.post("/tasks/recover")
def recover_interrupted_tasks(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    interrupted = db.query(Task).filter(Task.status.in_(["pending", "running", "retrying"])).all()
    for task in interrupted:
        task.status = "pending"
        background_tasks.add_task(run_agent, task.id, task.title, task.description)

    db.commit()
    return {"message": "Recovery scan complete", "requeued": len(interrupted)}


@router.get("/memory")
def get_memory(db: Session = Depends(get_db)):
    memories = db.query(Memory).all()
    return memories


@router.get("/health")
def health_check():
    return {"status": "healthy", "message": "Geta AI Agent is running"}
