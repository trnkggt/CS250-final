from contextlib import asynccontextmanager
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
app = FastAPI(lifespan=lifespan)


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
                     user: User = Depends(current_active_user),
                     session: AsyncSession = Depends(get_db)):
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