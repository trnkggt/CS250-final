import uuid
import enum
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import ForeignKey, Integer, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String, UUID, Enum

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

    reminders: Mapped["Reminder"] = relationship(
        back_populates="user",
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


class ReminderStatus(enum.Enum):
    finished = "finished"
    pending = "pending"

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plannable_id: Mapped[int] = mapped_column(Integer, nullable=False)

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    course_name: Mapped[str] = mapped_column(
        String(length=320), nullable=False
    )
    assignment_name: Mapped[str] = mapped_column(
        String(length=320), nullable=False
    )
    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status"),
        default=ReminderStatus.pending,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False,
    )
    user: Mapped["User"] = relationship(back_populates="reminders")



async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)
