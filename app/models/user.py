import uuid

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String, UUID

from app.core.database import Base, get_db

class User(SQLAlchemyBaseUserTableUUID, Base):
    username: Mapped[str] = mapped_column(
            String(length=320), nullable=False
        )

    canvas_token: Mapped["CanvasToken"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

class CanvasToken(Base):
    __tablename__ = "canvastoken"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token: Mapped[str] = mapped_column(String, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="canvas_token")


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)
