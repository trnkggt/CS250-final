from datetime import datetime

from pydantic import BaseModel


class Task(BaseModel):
    deadline: datetime
    grade: float
    course_name: str
    assignment_name: str