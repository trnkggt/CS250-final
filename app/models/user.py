from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String

from app.core.database import Base, get_db

class User(SQLAlchemyBaseUserTableUUID, Base):
    username: Mapped[str] = mapped_column(
            String(length=320), nullable=False
        )


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)
