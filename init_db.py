import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base
from app.database import engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database initialized successfully!") 