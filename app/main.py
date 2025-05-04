from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas import UserCreate, UserRead, UserUpdate, Task
from app.users import auth_backend, current_active_user, fastapi_users, \
    current_verified_user


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
    end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()  # next 2 weeks

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

        for item in planner_items:
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


@app.post(
    "/schedule/notification"
)
async def schedule_notification(
        task: Task,
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
            user_id=user.id
        )
        session.add(reminder)
        await session.commit()

        return {
            "task_id": result.id
        }
    except Exception as e:
        raise e