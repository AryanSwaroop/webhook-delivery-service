# Import required SQLAlchemy components
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool
from app.config import get_settings
from psycopg2_pool import PoolError

# Load application settings
settings = get_settings()

# Configure PostgreSQL connection with asyncpg driver
# Replace postgresql:// with postgresql+asyncpg:// for async support
engine = create_async_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    # Configure connection pool settings
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,           # Maximum number of connections in pool
    max_overflow=10,       # Maximum number of connections that can be created above pool_size
    pool_timeout=30,       # Timeout for getting a connection from pool
    pool_pre_ping=True,    # Enable connection health checks
    pool_recycle=1800,     # Recycle connections after 30 minutes
    # Configure PostgreSQL server settings
    connect_args={
        "server_settings": {
            "application_name": "webhook_service",
            "statement_timeout": "30000",  # 30 seconds
            "lock_timeout": "10000",       # 10 seconds
            "idle_in_transaction_session_timeout": "30000"  # 30 seconds
        }
    }
)

# Configure session factory for async database sessions
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent SQLAlchemy from expiring objects after commit
    autocommit=False,        # Disable autocommit
    autoflush=False          # Disable autoflush
)

# Create base class for declarative models
Base = declarative_base()

# Dependency function to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit transaction if no errors
        except PoolError as e:
            await session.rollback()  # Rollback on pool errors
            raise e
        except Exception as e:
            await session.rollback()  # Rollback on other errors
            raise e
        finally:
            await session.close()  # Always close session 