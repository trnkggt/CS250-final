from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas import UserCreate, UserRead, UserUpdate
from app.users import auth_backend, current_active_user, fastapi_users


from .core import sessionmanager, get_db
from .models import User, CanvasToken


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with sessionmanager.connect() as conn:
        await conn.execute(text("SELECT 1"))

    yield

    if sessionmanager._engine is not None:
        await sessionmanager.close()
app = FastAPI(lifespan=lifespan, response_class=ORJSONResponse)


@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}



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


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


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
    now = datetime.now(timezone.utc).isoformat()
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
        if response.status_code != 200:
            return {"error": "Failed to fetch assignments."}

        planner_items = response.json()
        assignments = []

        for item in planner_items:
            if item.get("plannable_type") == "assignment":
                plannable = item.get("plannable", {})
                submission = item.get("submissions", {})
                assignments.append({
                    "name": plannable.get("title"),
                    "deadline": plannable.get("due_at"),
                    "course": item.get("context_name"),
                    "submitted": submission.get("submitted"),
                    "graded": submission.get("graded")
                })

    return assignments
