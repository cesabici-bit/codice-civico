"""Base ingestor abstract class with SPARQL helpers."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from SPARQLWrapper import JSON, SPARQLWrapper
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.models import IngestionLog

logger = logging.getLogger(__name__)

SPARQL_PAGE_SIZE = 500
SPARQL_TIMEOUT = 30  # seconds
SPARQL_MAX_RETRIES = 3
SPARQL_BACKOFF_BASE = 2  # seconds


class BaseIngestor(ABC):
    """Abstract base for all data ingestors."""

    source_name: str

    @abstractmethod
    async def ingest(self, session: AsyncSession, *, limit: int | None = None) -> int:
        """Run ingestion. Returns number of records processed."""
        ...

    @abstractmethod
    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last checkpoint value for incremental ingestion."""
        ...

    def log_start(self) -> dict[str, object]:
        """Return ingestion log entry for start."""
        return {
            "source_name": self.source_name,
            "started_at": datetime.now(timezone.utc),
            "status": "running",
        }

    # ------------------------------------------------------------------
    # SPARQL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sparql_query(
        endpoint: str,
        query: str,
        *,
        timeout: int = SPARQL_TIMEOUT,
        max_retries: int = SPARQL_MAX_RETRIES,
    ) -> list[dict[str, str]]:
        """Execute a SPARQL SELECT and return rows as list of dicts.

        Each dict maps variable name -> string value.
        Retries with exponential backoff on failure.
        """
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(timeout)

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                raw = sparql.query().convert()
                response: dict = raw  # type: ignore[assignment]
                bindings: list[dict] = response.get("results", {}).get("bindings", [])
                return [
                    {k: v.get("value", "") for k, v in row.items()}
                    for row in bindings
                ]
            except Exception as exc:
                last_exc = exc
                wait = SPARQL_BACKOFF_BASE ** attempt
                logger.warning(
                    "SPARQL query attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt + 1,
                    max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        msg = f"SPARQL query failed after {max_retries} attempts"
        raise RuntimeError(msg) from last_exc

    @staticmethod
    def _sparql_paginated(
        endpoint: str,
        query_template: str,
        *,
        page_size: int = SPARQL_PAGE_SIZE,
        max_pages: int | None = None,
    ) -> list[dict[str, str]]:
        """Execute a paginated SPARQL query.

        query_template must contain {limit} and {offset} placeholders.
        Returns all rows concatenated.
        """
        all_rows: list[dict[str, str]] = []
        offset = 0
        page = 0

        while True:
            query = query_template.replace("{limit}", str(page_size)).replace(
                "{offset}", str(offset)
            )
            rows = BaseIngestor._sparql_query(endpoint, query)
            all_rows.extend(rows)

            logger.info(
                "SPARQL page %d: %d rows (total so far: %d)",
                page,
                len(rows),
                len(all_rows),
            )

            if len(rows) < page_size:
                break

            page += 1
            if max_pages is not None and page >= max_pages:
                logger.info("Reached max_pages=%d, stopping pagination.", max_pages)
                break

            offset += page_size

        return all_rows

    # ------------------------------------------------------------------
    # Ingestion log helpers
    # ------------------------------------------------------------------

    async def log_ingestion_start(self, session: AsyncSession) -> IngestionLog:
        """Create an IngestionLog entry with status='running'."""
        log_entry = IngestionLog(
            source_name=self.source_name,
            started_at=datetime.now(timezone.utc),
            status="running",
            records_processed=0,
        )
        session.add(log_entry)
        await session.flush()
        return log_entry

    async def log_ingestion_end(
        self,
        session: AsyncSession,
        log_entry: IngestionLog,
        *,
        records: int,
        status: str = "success",
        errors: dict | None = None,
        checkpoint: str | None = None,
    ) -> None:
        """Update an IngestionLog entry with final status."""
        log_entry.finished_at = datetime.now(timezone.utc)
        log_entry.status = status
        log_entry.records_processed = records
        log_entry.errors = errors
        log_entry.checkpoint_value = checkpoint
        await session.flush()

    async def get_last_checkpoint(self, session: AsyncSession) -> str | None:
        """Get the checkpoint from the last successful ingestion."""
        stmt = (
            select(IngestionLog.checkpoint_value)
            .where(
                IngestionLog.source_name == self.source_name,
                IngestionLog.status == "success",
            )
            .order_by(IngestionLog.finished_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row
