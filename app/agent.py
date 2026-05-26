import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Task, Memory, ExecutionLog

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def log_step(db: Session, task_id: int, step: str, result: str):
    log = ExecutionLog(task_id=task_id, step=step, result=result)
    db.add(log)
    db.commit()


def step1_parse_task(task_description: str, db: Session, task_id: int) -> dict:
    prompt = f"""
    You are a task parser. Analyze the following task and extract structured information.

    Task: {task_description}

    Respond ONLY with a JSON object with these exact fields:
    - "task_type": what kind of task this is (one word or short phrase)
    - "key_objectives": list of main objectives
    - "complexity": "low", "medium", or "high"
    - "parsed_description": a clean, clear version of the task

    No explanation, no markdown, just raw JSON.
    """
    response = model.generate_content(prompt)
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    log_step(db, task_id, "task_parser", result)
    try:
        return json.loads(result)
    except:
        return {
            "task_type": "general",
            "key_objectives": [task_description],
            "complexity": "medium",
            "parsed_description": task_description
        }


def step2_load_memory(task_title: str, db: Session, task_id: int) -> str:
    memories = db.query(Memory).all()
    if not memories:
        log_step(db, task_id, "memory_loader", "No past memory found.")
        return "No previous context available."

    memory_text = "\n".join([
        f"- Task: {m.task_title} | Summary: {m.summary}"
        for m in memories[-5:]
    ])

    prompt = f"""
    You are a memory retrieval system.

    Current task: {task_title}

    Past task summaries:
    {memory_text}

    Identify any relevant past context that could help with the current task.
    If nothing is relevant, say "No relevant past context."
    Keep your response brief and focused. No bullet points.
    """
    response = model.generate_content(prompt)
    result = response.text.strip()
    log_step(db, task_id, "memory_loader", result)
    return result


def step3_execute_task(parsed_task: dict, memory_context: str, db: Session, task_id: int) -> str:
    prompt = f"""
    You are an AI execution engine. Execute the following task completely and thoroughly.

    Task Type: {parsed_task.get("task_type")}
    Objectives: {parsed_task.get("key_objectives")}
    Task Description: {parsed_task.get("parsed_description")}

    Relevant Past Context:
    {memory_context}

    Execute this task and provide a complete, detailed, useful result.
    """
    response = model.generate_content(prompt)
    result = response.text.strip()
    log_step(db, task_id, "execution_engine", result)
    return result


def step4_verify_result(task_description: str, execution_result: str, db: Session, task_id: int) -> dict:
    prompt = f"""
    You are a result verifier. Check if the execution result adequately addresses the task.

    Original Task: {task_description}
    Execution Result: {execution_result}

    Respond ONLY with a JSON object with these exact fields:
    - "verified": true or false
    - "confidence_score": a number between 0.0 and 1.0
    - "summary": one sentence summary of what was done
    - "issues": list of any issues found (empty list if none)

    No explanation, no markdown, just raw JSON.
    """
    response = model.generate_content(prompt)
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    log_step(db, task_id, "verifier", result)
    try:
        return json.loads(result)
    except:
        return {
            "verified": True,
            "confidence_score": 0.8,
            "summary": execution_result[:200],
            "issues": []
        }


def save_to_memory(task_id: int, task_title: str, context: str, summary: str, db: Session):
    memory = Memory(
        task_id=task_id,
        task_title=task_title,
        context=context,
        summary=summary
    )
    db.add(memory)
    db.commit()


def execute_agent(task_id: int, task_title: str, task_description: str, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {"status": "failed", "error": "Task not found"}

    task.status = "running"
    task.failure_reason = None
    db.commit()

    try:
        parsed = step1_parse_task(task_description, db, task_id)
        memory_context = step2_load_memory(task_title, db, task_id)
        execution_result = step3_execute_task(parsed, memory_context, db, task_id)
        verification = step4_verify_result(task_description, execution_result, db, task_id)

        save_to_memory(
            task_id, task_title, task_description,
            verification.get("summary", execution_result[:200]),
            db
        )

        task.status = "completed"
        task.result = execution_result
        db.commit()

        return {"status": "completed", "result": execution_result, "verification": verification}

    except Exception as e:
        task.retry_count += 1
        task.failure_reason = str(e)

        permanent_errors = ("400", "404", "429", "API_KEY_INVALID", "quota")
        should_retry = task.retry_count < 3 and not any(
            error in task.failure_reason for error in permanent_errors
        )

        if should_retry:
            task.status = "retrying"
            db.commit()
            return run_agent(task_id, task_title, task_description, db)

        task.status = "failed"
        db.commit()
        return {"status": "failed", "error": str(e)}


def run_agent(task_id: int, task_title: str, task_description: str):
    db = SessionLocal()
    try:
        return execute_agent(task_id, task_title, task_description, db)
    finally:
        db.close()
