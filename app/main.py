from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List

import httpx
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, and_
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.requests import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from celery.result import AsyncResult

from app.schemas import UserCreate, UserRead, UserUpdate, TaskSchema, \
    ReminderSchema
from app.users import auth_backend, current_active_user, fastapi_users, \
    current_verified_user
from .celery import celery


from .core import sessionmanager, get_db
from .models import User, CanvasToken, Reminder, ReminderStatus
from .tasks import send_notification


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with sessionmanager.connect() as conn:
        await conn.execute(text("SELECT 1"))

    yield

    if sessionmanager._engine is not None:
        await sessionmanager.close()
app = FastAPI(lifespan=lifespan, response_class=ORJSONResponse,
              docs_url="/dev/api/docs")

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return ORJSONResponse(
        status_code=400,
        content={"detail": "A database error occurred."}
    )

@app.post("/save/token")
async def save_token(token: str,
                     session: AsyncSession = Depends(get_db),
                     user: User = Depends(current_active_user)):
    result = await session.execute(
        select(CanvasToken).where(CanvasToken.user_id == user.id)
    )
    existing_token = result.scalar_one_or_none()

    if existing_token:
        existing_token.token = token
    else:
        token = CanvasToken(token=token, user_id=user.id)
        session.add(token)

    await session.commit()
    return {"message": "Token saved"}


@app.get("/upcoming/assignments")
async def get_assignments(
        session: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)):
    result = await session.execute(
        select(CanvasToken).where(CanvasToken.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    now = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    url = f"https://sdsu.instructure.com/"
    headers = {"Authorization": f"Bearer {token.token}"}


    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{url}/api/v1/planner/items",
            params={
                "start_date": now,
                "end_date": end
            },
            headers=headers
        )
        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json()["message"]
            )

        planner_items = response.json()
        assignments = []

        stmt = select(Reminder.plannable_id).where(
            and_(
                Reminder.user_id == user.id,
                Reminder.status == ReminderStatus.pending
            )
        )
        user_reminders = set(await session.scalars(stmt))

        for item in planner_items:
            if item.get('plannable_id') not in user_reminders:
                if item.get("plannable_type") == "assignment":
                    plannable = item.get("plannable", {})
                    submission = item.get("submissions", {})
                    assignments.append({
                        "plannable_id": item.get("plannable_id"),
                        "name": plannable.get("title"),
                        "deadline": plannable.get("due_at"),
                        "course": item.get("context_name"),
                        "submitted": submission.get("submitted"),
                        "graded": submission.get("graded"),
                        "points_possible": item.get("plannable").get("points_possible")
                    })

    return assignments

@app.get("/active/reminders",
         response_model=List[ReminderSchema],
         status_code=200,
         description="Get reminder statuses for user.")
async def get_reminders(
        session: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user)
):
    stmt = select(Reminder).where(
        and_(
            Reminder.user_id == user.id,
            Reminder.status == ReminderStatus.pending
        )
    )
    reminders = await session.execute(stmt)

    return reminders.scalars().all()


@app.delete("/delete/reminder",
            status_code=204,
            description="Delete reminder by its ID.")
async def delete_reminder(
        task_id: str = Query(..., min_length=1),
        session: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user),
):
    task_result = AsyncResult(task_id, app=celery)

    if task_result.state in {"SUCCESS", "FAILURE", "REVOKED"}:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task. Current state: {task_result.state}"
        )

    task_result.revoke(terminate=True)

    stmt = delete(Reminder).where(
        and_(
            Reminder.user_id == user.id,
            Reminder.task_id == task_id
        )
    )
    db_result = await session.execute(stmt)
    await session.commit()

    if db_result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found or not authorized."
        )

    return

@app.post(
    "/schedule/notification",
    status_code=200,
    description="Schedule notification to user."
)
async def schedule_notification(
        task: TaskSchema,
        session: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user),
):

    try:
        notification_time = task.deadline - timedelta(hours=1)

        result = send_notification.apply_async(
            args=[user.email, task.model_dump()],
            eta=notification_time
        )

        reminder = Reminder(
            plannable_id=task.plannable_id,
            task_id=result.id,
            user_id=user.id,
            course_name=task.course_name,
            assignment_name=task.assignment_name,
            deadline=task.deadline
        )
        session.add(reminder)
        await session.commit()

        return {
            "task_id": result.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Unable to schedule notification"
        )

@app.post(
    "/send/fake/notification",
    status_code=200,
    description="Schedule notification to user."
)
async def schedule_fake_notification(
        task: TaskSchema,
        session: AsyncSession = Depends(get_db),
        user: User = Depends(current_active_user),
):

    try:
        result = send_notification.apply_async(
            args=[user.email, task.model_dump()],
            eta=task.deadline
        )

        reminder = Reminder(
            plannable_id=task.plannable_id,
            task_id=result.id,
            user_id=user.id,
            course_name=task.course_name,
            assignment_name=task.assignment_name,
            deadline=task.deadline
        )
        session.add(reminder)
        await session.commit()

        return {
            "task_id": result.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Unable to schedule notification"
        )