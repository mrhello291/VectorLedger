from __future__ import annotations

import re

from psycopg import AsyncConnection, sql

from vectorledger.models import Artifact, Document

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresConnector:
    """Adapter for a company's chunk table, separate from the ledger database."""

    name = "postgres"

    def __init__(
        self,
        dsn: str,
        table: str = "rag_chunks",
        tenant_column: str = "tenant_id",
        document_column: str = "document_id",
        permissions_column: str = "allowed_principals",
    ) -> None:
        identifiers = (table, tenant_column, document_column, permissions_column)
        if not all(_IDENTIFIER.fullmatch(value) for value in identifiers):
            raise ValueError("table and column names must be simple SQL identifiers")
        self.dsn = dsn
        self.table = table
        self.tenant_column = tenant_column
        self.document_column = document_column
        self.permissions_column = permissions_column

    def _where(self) -> sql.Composed:
        return sql.SQL("{} = %s AND {} = %s").format(
            sql.Identifier(self.tenant_column), sql.Identifier(self.document_column)
        )

    async def delete(self, document: Document, artifacts: list[Artifact]) -> int:
        async with (
            await AsyncConnection.connect(self.dsn) as connection,
            connection.cursor() as cursor,
        ):
            query = (
                sql.SQL("DELETE FROM {} WHERE ").format(sql.Identifier(self.table)) + self._where()
            )
            await cursor.execute(query, (document.tenant_id, document.document_id))
            return cursor.rowcount

    async def apply_permissions(self, document: Document, artifacts: list[Artifact]) -> int:
        async with (
            await AsyncConnection.connect(self.dsn) as connection,
            connection.cursor() as cursor,
        ):
            query = (
                sql.SQL("UPDATE {} SET {} = %s WHERE ").format(
                    sql.Identifier(self.table), sql.Identifier(self.permissions_column)
                )
                + self._where()
            )
            await cursor.execute(
                query,
                (
                    list(document.allowed_principals),
                    document.tenant_id,
                    document.document_id,
                ),
            )
            return cursor.rowcount

    async def discover(self, document: Document) -> list[dict[str, object]]:
        async with (
            await AsyncConnection.connect(self.dsn) as connection,
            connection.cursor() as cursor,
        ):
            query = (
                sql.SQL("SELECT * FROM {} WHERE ").format(sql.Identifier(self.table))
                + self._where()
            )
            await cursor.execute(query, (document.tenant_id, document.document_id))
            columns = [description.name for description in cursor.description or []]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row, strict=True)) for row in rows]
