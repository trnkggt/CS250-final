import contextlib
from typing import Any, AsyncIterator

from sqlalchemy import create_engine

from app.core import settings
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False,
                                                bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None


    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as conn:
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

class SyncDatabaseSessionManager:
    def __init__(self, db_url: str, engine_kwargs: dict = {}):
        self._engine = create_engine(db_url, **engine_kwargs)
        self._sessionmaker = sessionmaker(bind=self._engine, autocommit=False, autoflush=False)

    def get_session(self) -> Session:
        return self._sessionmaker()

sync_sessionmanager = SyncDatabaseSessionManager(
    settings.database_url_sync.unicode_string(),
    {"echo": True}
)

@contextlib.contextmanager
def get_sync_db():
    db = sync_sessionmanager.get_session()
    try:
        yield db
    finally:
        db.close()


sessionmanager = DatabaseSessionManager(settings.database_url.unicode_string(), {"echo": True})

async def get_db():
    async with sessionmanager.session() as session:
        yield session