"""database.py"""

from typing import Optional
from psycopg_pool import AsyncConnectionPool
import logging
import os
import dotenv
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


# get the database URI from environment variables
dotenv.load_dotenv()
DB_URI = os.getenv("DATABASE_URL")


class DatabaseManager:
    """Database connection manager, using singleton pattern to manage all database connections"""

    _instance: Optional["DatabaseManager"] = None
    _pool: Optional[AsyncConnectionPool] = None
    _last_health_check: Optional[datetime] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls, db_uri: str, max_size: int = 20) -> None:
        """
        Initialize the database connection pool

        Args:
            db_uri: database connection URI
            max_size: maximum number of connections in the connection pool
        """
        if cls._pool is not None:
            # if the connection pool already exists, return directly to avoid repeated initialization
            logger.debug(
                "Database connection pool already exists, skipping initialization"
            )
            return

        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }

        try:
            cls._pool = AsyncConnectionPool(
                conninfo=db_uri, max_size=max_size, open=False, kwargs=connection_kwargs
            )
            await cls._pool.open()
            cls._last_health_check = (
                datetime.now()
            )  # set the health check time when initializing
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Database connection pool initialization failed: {str(e)}")
            raise

    @classmethod
    async def get_pool(cls, max_retries: int = 3) -> AsyncConnectionPool:
        """
        Get the database connection pool, with retry mechanism

        Args:
            max_retries: maximum number of retries

        Returns:
            AsyncConnectionPool: database connection pool instance

        Raises:
            RuntimeError: if the connection pool is not initialized or the retry fails
        """
        if cls._pool is None:
            if not DB_URI:
                raise RuntimeError(
                    "DATABASE_URL is not configured; please set it in your environment/.env file"
                )
            await cls.initialize(DB_URI)

        # only perform health check if the last health check is more than 5 minutes ago
        now = datetime.now()
        if (
            cls._last_health_check is None
            or (now - cls._last_health_check).total_seconds() > 300
        ):
            if not await cls._check_pool_health():
                for i in range(max_retries):
                    try:
                        await cls._pool.close()
                        await cls._pool.open()
                        if await cls._check_pool_health():
                            logger.info(
                                "Database connection pool reconnected successfully"
                            )
                            break
                    except Exception as e:
                        if i == max_retries - 1:
                            logger.error(
                                f"Database connection pool reconnection failed: {str(e)}"
                            )
                            raise RuntimeError(
                                "Database connection pool reconnection failed"
                            )
                        await asyncio.sleep(1)

        return cls._pool

    @classmethod
    async def _check_pool_health(cls) -> bool:
        """Check the health status of the connection pool"""
        if cls._pool is None:
            return False

        try:
            async with cls._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            cls._last_health_check = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Database connection pool health check failed: {str(e)}")
            return False

    @classmethod
    async def close(cls) -> None:
        """Close the database connection pool"""
        if cls._pool is not None:
            try:
                await cls._pool.close()
                cls._pool = None
                logger.info("Database connection pool closed successfully")
            except Exception as e:
                logger.error(f"Failed to close database connection pool: {str(e)}")
                raise
