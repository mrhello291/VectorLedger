from __future__ import annotations

import json
from typing import Any, cast

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from vectorledger.models import (
    Artifact,
    ArtifactState,
    DesiredState,
    Document,
    DocumentKey,
    Receipt,
    TargetResult,
    VerificationStatus,
)


class PostgresStore:
    def __init__(self, dsn: str) -> None:
        self.pool = AsyncConnectionPool(dsn, min_size=1, max_size=10, open=False)

    async def initialize(self) -> None:
        await self.pool.open()
        migration = (
            __import__("pathlib").Path(__file__).parent.parent / "migrations" / "001_init.sql"
        )
        async with self.pool.connection() as connection:
            await connection.execute(migration.read_text())

    async def close(self) -> None:
        await self.pool.close()

    async def upsert_document(self, document: Document) -> Document:
        query = """
            INSERT INTO vl_documents
                (tenant_id, document_id, version, source_uri, content_hash, desired_state,
                 allowed_principals, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, document_id) DO UPDATE SET
                version = EXCLUDED.version,
                source_uri = EXCLUDED.source_uri,
                content_hash = EXCLUDED.content_hash,
                desired_state = EXCLUDED.desired_state,
                allowed_principals = EXCLUDED.allowed_principals,
                updated_at = EXCLUDED.updated_at
            WHERE vl_documents.version <= EXCLUDED.version
            RETURNING *
        """
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                query,
                (
                    document.tenant_id,
                    document.document_id,
                    document.version,
                    document.source_uri,
                    document.content_hash,
                    document.desired_state.value,
                    list(document.allowed_principals),
                    document.updated_at,
                ),
            )
            row = await cursor.fetchone()
        if row is None:
            raise ValueError("document version cannot move backwards")
        return self._document(row)

    async def get_document(self, key: DocumentKey) -> Document | None:
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                "SELECT * FROM vl_documents WHERE tenant_id = %s AND document_id = %s",
                (key.tenant_id, key.document_id),
            )
            row = await cursor.fetchone()
        return self._document(row) if row else None

    async def list_documents(self) -> list[Document]:
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute("SELECT * FROM vl_documents ORDER BY tenant_id, document_id")
            rows = await cursor.fetchall()
        return [self._document(row) for row in rows]

    async def add_artifact(self, artifact: Artifact) -> Artifact:
        query = """
            INSERT INTO vl_artifacts
                (artifact_id, tenant_id, document_id, document_version, target, locator,
                 state, last_error, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (artifact_id) DO UPDATE SET
                locator = EXCLUDED.locator,
                state = EXCLUDED.state,
                last_error = EXCLUDED.last_error,
                updated_at = EXCLUDED.updated_at
            RETURNING *
        """
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                query,
                (
                    artifact.artifact_id,
                    artifact.tenant_id,
                    artifact.document_id,
                    artifact.document_version,
                    artifact.target,
                    json.dumps(artifact.locator),
                    artifact.state.value,
                    artifact.last_error,
                    artifact.updated_at,
                ),
            )
            row = await cursor.fetchone()
        assert row is not None
        return self._artifact(row)

    async def list_artifacts(self, key: DocumentKey) -> list[Artifact]:
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(
                "SELECT * FROM vl_artifacts WHERE tenant_id = %s AND document_id = %s",
                (key.tenant_id, key.document_id),
            )
            rows = await cursor.fetchall()
        return [self._artifact(row) for row in rows]

    async def mark_artifacts(
        self, key: DocumentKey, target: str, state: ArtifactState, error: str | None = None
    ) -> None:
        async with self.pool.connection() as connection:
            await connection.execute(
                """UPDATE vl_artifacts SET state = %s, last_error = %s, updated_at = now()
                   WHERE tenant_id = %s AND document_id = %s AND target = %s""",
                (state.value, error, key.tenant_id, key.document_id, target),
            )

    async def save_receipt(self, receipt: Receipt) -> Receipt:
        async with self.pool.connection() as connection:
            await connection.execute(
                """INSERT INTO vl_receipts
                   (receipt_id, tenant_id, document_id, payload, signature, checked_at)
                   VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                   ON CONFLICT (receipt_id) DO NOTHING""",
                (
                    receipt.receipt_id,
                    receipt.tenant_id,
                    receipt.document_id,
                    json.dumps(receipt.payload()),
                    receipt.signature,
                    receipt.checked_at,
                ),
            )
        return receipt

    async def get_receipt(self, receipt_id: str) -> Receipt | None:
        async with (
            self.pool.connection() as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute("SELECT * FROM vl_receipts WHERE receipt_id = %s", (receipt_id,))
            row = await cursor.fetchone()
        if not row:
            return None
        payload = row["payload"]
        return Receipt(
            receipt_id=payload["receipt_id"],
            tenant_id=payload["tenant_id"],
            document_id=payload["document_id"],
            document_version=payload["document_version"],
            desired_state=payload["desired_state"],
            status=VerificationStatus(payload["status"]),
            checked_at=row["checked_at"],
            targets=[TargetResult(**target) for target in payload["targets"]],
            signature=row["signature"],
        )

    @staticmethod
    def _document(row: dict[str, object]) -> Document:
        return Document(
            tenant_id=str(row["tenant_id"]),
            document_id=str(row["document_id"]),
            version=int(str(row["version"])),
            source_uri=str(row["source_uri"]),
            content_hash=str(row["content_hash"]) if row["content_hash"] else None,
            desired_state=DesiredState(str(row["desired_state"])),
            allowed_principals=tuple(row["allowed_principals"] or []),  # type: ignore[arg-type]
            updated_at=row["updated_at"],  # type: ignore[arg-type]
        )

    @staticmethod
    def _artifact(row: dict[str, object]) -> Artifact:
        return Artifact(
            artifact_id=str(row["artifact_id"]),
            tenant_id=str(row["tenant_id"]),
            document_id=str(row["document_id"]),
            document_version=int(str(row["document_version"])),
            target=str(row["target"]),
            locator=cast(dict[str, Any], row["locator"]),
            state=ArtifactState(str(row["state"])),
            last_error=str(row["last_error"]) if row["last_error"] else None,
            updated_at=row["updated_at"],  # type: ignore[arg-type]
        )
