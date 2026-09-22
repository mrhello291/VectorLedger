from __future__ import annotations

import asyncio
from dataclasses import replace

from vectorledger.models import Artifact, ArtifactState, Document, DocumentKey, Receipt, utcnow


class MemoryStore:
    """Deterministic store for tests and local development."""

    def __init__(self) -> None:
        self.documents: dict[DocumentKey, Document] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.receipts: dict[str, Receipt] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def upsert_document(self, document: Document) -> Document:
        async with self._lock:
            current = self.documents.get(document.key)
            if current and document.version < current.version:
                raise ValueError("document version cannot move backwards")
            self.documents[document.key] = replace(document)
            return replace(document)

    async def get_document(self, key: DocumentKey) -> Document | None:
        value = self.documents.get(key)
        return replace(value) if value else None

    async def list_documents(self) -> list[Document]:
        return [replace(value) for value in self.documents.values()]

    async def add_artifact(self, artifact: Artifact) -> Artifact:
        async with self._lock:
            existing = self.artifacts.get(artifact.artifact_id)
            if existing and (
                existing.tenant_id != artifact.tenant_id
                or existing.document_id != artifact.document_id
                or existing.target != artifact.target
                or artifact.document_version < existing.document_version
            ):
                raise ValueError(
                    f"artifact id {artifact.artifact_id} belongs to different or newer lineage"
                )
            self.artifacts[artifact.artifact_id] = replace(artifact)
            return replace(artifact)

    async def list_artifacts(self, key: DocumentKey) -> list[Artifact]:
        return [
            replace(value)
            for value in self.artifacts.values()
            if value.tenant_id == key.tenant_id and value.document_id == key.document_id
        ]

    async def mark_artifacts(
        self, key: DocumentKey, target: str, state: ArtifactState, error: str | None = None
    ) -> None:
        async with self._lock:
            for artifact_id, value in tuple(self.artifacts.items()):
                if (
                    value.tenant_id == key.tenant_id
                    and value.document_id == key.document_id
                    and value.target == target
                ):
                    self.artifacts[artifact_id] = replace(
                        value, state=state, last_error=error, updated_at=utcnow()
                    )

    async def save_receipt(self, receipt: Receipt) -> Receipt:
        async with self._lock:
            self.receipts[receipt.receipt_id] = replace(receipt)
            return replace(receipt)

    async def get_receipt(self, receipt_id: str) -> Receipt | None:
        value = self.receipts.get(receipt_id)
        return replace(value) if value else None
