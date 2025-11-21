from __future__ import annotations
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def __init__(self, task_id: str, status: str, progress: str, email: Optional[str] = None,
                 source_info: Optional[Dict[str, Any]] = None):
        self.task_id: str = task_id
        self.status: str = status
        self.progress: str = progress
        self.email: Optional[str] = email
        self.source_info: Optional[Dict[str, Any]] = source_info or {}
        self.detailed_results: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}
        self.result_file: Optional[str] = None
        self.error: Optional[str] = None
        self.timestamp: datetime = datetime.now()

    def __repr__(self):
        return (f"TaskStatus(task_id='{self.task_id}', status='{self.status}', "
                f"progress='{self.progress}', email='{self.email}', "
                f"source_info={self.source_info})")

active_tasks: Dict[str, TaskStatus] = {}

def create_task(email: Optional[str] = None, source_info: Optional[Dict[str, Any]] = None) -> str:
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = TaskStatus(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress="Инициализация...",
        email=email,
        source_info=source_info or {}
    )
    return task_id

def get_task(task_id: str) -> Optional[TaskStatus]:
    return active_tasks.get(task_id)

def update_task_status(task_id: str, status: str, progress: str = None, error: str = None):
    if task_id in active_tasks:
        task = active_tasks[task_id]
        task.status = status
        if progress is not None:
            task.progress = progress
        if error is not None:
            task.error = error

