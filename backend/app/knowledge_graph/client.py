"""Neo4j async driver connection manager.

Provides connection pooling, session factory, and health checks for
the knowledge graph database.
"""

from __future__ import annotations

import asyncio
from typing import Any, Self

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession, AsyncTransaction

from app.config import Settings, get_settings

logger = structlog.get_logger()


class Neo4jClient:
    """Async Neo4j driver wrapper with connection pooling and health checks.

    Usage::

        client = Neo4jClient()
        await client.connect()
        async with client.session() as session:
            result = await session.run("MATCH (n) RETURN count(n)")
        await client.close()
    """

    _instance: Neo4jClient | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._driver: AsyncDriver | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Initialise the async Neo4j driver with connection pooling."""
        if self._driver is not None:
            return

        self._driver = AsyncGraphDatabase.driver(
            self._settings.neo4j_uri,
            auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            max_connection_pool_size=50,
            connection_acquisition_timeout=30.0,
            max_transaction_retry_time=15.0,
        )

        logger.info(
            "neo4j.connected",
            uri=self._settings.neo4j_uri,
            user=self._settings.neo4j_user,
        )

    async def close(self) -> None:
        """Gracefully shut down the driver and release pooled connections."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("neo4j.disconnected")

    # ------------------------------------------------------------------
    # Session factory
    # ------------------------------------------------------------------

    def session(self, database: str = "neo4j", **kwargs: Any) -> AsyncSession:
        """Return an async session bound to *database*.

        Intended for use as an async context manager::

            async with client.session() as s:
                ...
        """
        self._ensure_driver()
        assert self._driver is not None  # narrowing for type checker
        return self._driver.session(database=database, **kwargs)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """Run a single Cypher query and return a list of record dicts.

        This is a convenience wrapper that acquires a session, runs the query
        inside an implicit transaction, and converts each ``Record`` to a
        plain ``dict``.
        """
        self._ensure_driver()
        async with self.session(database=database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """Execute a write transaction with automatic retries.

        Wraps the query in an explicit write transaction so Neo4j can
        retry on transient errors (leader switches, etc.).
        """
        self._ensure_driver()

        async def _work(tx: AsyncTransaction) -> list[dict[str, Any]]:
            result = await tx.run(query, parameters or {})
            return await result.data()

        async with self.session(database=database) as session:
            return await session.execute_write(_work)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Verify connectivity and return server info.

        Returns a dict with ``status`` ("healthy" | "unhealthy"),
        ``server_address``, and ``agent`` string from the driver.
        """
        try:
            self._ensure_driver()
            assert self._driver is not None
            info = await self._driver.get_server_info()
            return {
                "status": "healthy",
                "server_address": str(info.address),
                "agent": info.agent,
                "protocol_version": str(info.protocol_version),
            }
        except Exception as exc:
            logger.error("neo4j.health_check_failed", error=str(exc))
            return {
                "status": "unhealthy",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Schema initialisation (indexes & constraints)
    # ------------------------------------------------------------------

    async def ensure_indexes(self) -> None:
        """Create indexes and uniqueness constraints used by the KG module.

        Safe to call repeatedly -- each statement uses ``IF NOT EXISTS``.
        """
        statements: list[str] = [
            # Uniqueness constraints
            "CREATE CONSTRAINT creator_id_unique IF NOT EXISTS "
            "FOR (c:Creator) REQUIRE c.creator_id IS UNIQUE",
            "CREATE CONSTRAINT content_id_unique IF NOT EXISTS "
            "FOR (c:Content) REQUIRE c.content_id IS UNIQUE",
            "CREATE CONSTRAINT topic_name_unique IF NOT EXISTS "
            "FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT keyword_name_unique IF NOT EXISTS "
            "FOR (k:Keyword) REQUIRE k.name IS UNIQUE",
            # Indexes for common lookups
            "CREATE INDEX content_type_idx IF NOT EXISTS "
            "FOR (c:Content) ON (c.content_type)",
            "CREATE INDEX trend_velocity_idx IF NOT EXISTS "
            "FOR (t:Trend) ON (t.velocity)",
            "CREATE INDEX audience_segment_idx IF NOT EXISTS "
            "FOR (a:AudienceSegment) ON (a.name)",
            "CREATE INDEX idea_status_idx IF NOT EXISTS "
            "FOR (i:Idea) ON (i.status)",
        ]
        async with self.session() as session:
            for stmt in statements:
                await session.run(stmt)
        logger.info("neo4j.indexes_ensured", count=len(statements))

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    async def get_instance(cls, settings: Settings | None = None) -> Neo4jClient:
        """Return (or create) a module-level singleton client.

        Thread-safe via an ``asyncio.Lock``.
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(settings)
                await cls._instance.connect()
                await cls._instance.ensure_indexes()
            return cls._instance

    @classmethod
    async def close_instance(cls) -> None:
        """Shut down the singleton, if it exists."""
        async with cls._lock:
            if cls._instance is not None:
                await cls._instance.close()
                cls._instance = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_driver(self) -> None:
        if self._driver is None:
            raise RuntimeError(
                "Neo4jClient is not connected. "
                "Call `await client.connect()` or use the async context manager."
            )


# ------------------------------------------------------------------
# Module-level convenience function
# ------------------------------------------------------------------

async def get_neo4j_client(settings: Settings | None = None) -> Neo4jClient:
    """Return the global Neo4jClient singleton.

    Suitable for use as a FastAPI dependency::

        @router.get("/graph/health")
        async def graph_health(client: Neo4jClient = Depends(get_neo4j_client)):
            return await client.health_check()
    """
    return await Neo4jClient.get_instance(settings)
