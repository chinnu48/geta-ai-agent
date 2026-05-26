from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    result = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Memory(Base):
    __tablename__ = "memory"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    task_title = Column(String(255), nullable=False)
    context = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    step = Column(String(100), nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())