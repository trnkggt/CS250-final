import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskReminderBase(BaseModel):
    plannable_id: int
    course_name: str
    assignment_name: str
    deadline: datetime

class ReminderSchema(TaskReminderBase):
    task_id: uuid.UUID


class TaskSchema(TaskReminderBase):
    grade: float
