from datetime import datetime

from pydantic import BaseModel


class Task(BaseModel):
    plannable_id: int
    deadline: datetime
    grade: float
    course_name: str
    assignment_name: str