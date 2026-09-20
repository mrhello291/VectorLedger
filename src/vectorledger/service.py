from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import timedelta
from uuid import uuid4

from vectorledger.connectors.base import Connector
from vectorledger.models import (
    Artifact,
    ArtifactState,
    DeletionMode,
    DesiredState,
    Document,
    DocumentKey,
    Receipt,
    TargetResult,
    VerificationStatus,
    utcnow,
)
from vectorledger.receipts import ReceiptSigner
from vectorledger.store.base import LedgerStore


class NotFoundError(LookupError):
    pass


class InvalidStateError(ValueError):
    pass


class VectorLedgerService:
    def __init__(
        self,
        store: LedgerStore,
        connectors: dict[str, Connector],
        signer: ReceiptSigner,
        scheduled_deletion_grace: timedelta = timedelta(days=3),
    ) -> None:
        if scheduled_deletion_grace <= timedelta(0):
            raise ValueError("scheduled deletion grace period must be positive")
        self.store = store
        self.connectors = connectors
        self.signer = signer
        self.scheduled_deletion_grace = scheduled_deletion_grace
        self._document_locks: defaultdict[DocumentKey, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def register_document(self, document: Document) -> Document:
        current = await self.store.get_document(document.key)
        if current and current.desired_state != DesiredState.ACTIVE:
            raise InvalidStateError(
                "document is pending deletion or deleted; restore it before registration"
            )
        return await self.store.upsert_document(document)

    async def register_artifact(self, artifact: Artifact) -> Artifact:
        document = await self.store.get_document(
            DocumentKey(artifact.tenant_id, artifact.document_id)
        )
        if not document:
            raise NotFoundError("register the document before registering artifacts")
        if document.desired_state != DesiredState.ACTIVE:
            raise InvalidStateError(
                "document is pending deletion or deleted; restore it before adding artifacts"
            )
        if artifact.document_version > document.version:
            raise ValueError("artifact refers to a future document version")
        return await self.store.add_artifact(artifact)

    async def request_deletion(
        self,
        key: DocumentKey,
        version: int | None = None,
        mode: DeletionMode = DeletionMode.IMMEDIATE,
        grace_period: timedelta | None = None,
    ) -> Receipt:
        document = await self._get_document(key)

        # A verified hard deletion cannot become a recoverable scheduled deletion.
        # Call restore_document and re-ingest instead.
        if document.desired_state == DesiredState.DELETED:
            return await self.reconcile(key)

        now = utcnow()
        document.version = version or (document.version + 1)
        document.deletion_mode = mode
        document.deletion_requested_at = document.deletion_requested_at or now

        if mode == DeletionMode.IMMEDIATE:
            document.desired_state = DesiredState.DELETED
            document.purge_after = None
        else:
            grace = grace_period or self.scheduled_deletion_grace
            if grace <= timedelta(0):
                raise ValueError("scheduled deletion grace period must be positive")
            document.desired_state = DesiredState.PENDING_DELETION
            document.allowed_principals = ()
            document.purge_after = document.purge_after or (now + grace)

        document.updated_at = now
        await self.store.upsert_document(document)
        return await self.reconcile(key)

    async def change_permissions(
        self, key: DocumentKey, allowed_principals: tuple[str, ...], version: int | None = None
    ) -> Receipt:
        document = await self._get_document(key)
        if document.desired_state != DesiredState.ACTIVE:
            raise InvalidStateError(
                "document is pending deletion or deleted; use the restore endpoint"
            )
        document.version = version or (document.version + 1)
        document.allowed_principals = allowed_principals
        document.updated_at = utcnow()
        await self.store.upsert_document(document)
        return await self.reconcile(key)

    async def restore_document(
        self,
        key: DocumentKey,
        allowed_principals: tuple[str, ...],
        version: int | None = None,
    ) -> tuple[Document, Receipt | None, bool]:
        document = await self._get_document(key)
        reingestion_required = document.desired_state == DesiredState.DELETED
        document.version = version or (document.version + 1)
        document.desired_state = DesiredState.ACTIVE
        document.allowed_principals = allowed_principals
        document.deletion_mode = None
        document.deletion_requested_at = None
        document.purge_after = None
        document.updated_at = utcnow()
        document = await self.store.upsert_document(document)

        # Scheduled deletion only quarantines records, so ACLs can be restored in
        # place. Hard-deleted records must be rebuilt by the ingestion pipeline.
        receipt = None if reingestion_required else await self.reconcile(key)
        return document, receipt, reingestion_required

    async def verify(self, key: DocumentKey) -> Receipt:
        return await self.reconcile(key, mutate=False)

    async def reconcile(self, key: DocumentKey, mutate: bool = True) -> Receipt:
        async with self._document_locks[key]:
            document = await self._get_document(key)
            if (
                mutate
                and document.desired_state == DesiredState.PENDING_DELETION
                and document.purge_after is not None
                and document.purge_after <= utcnow()
            ):
                document.desired_state = DesiredState.DELETED
                document.updated_at = utcnow()
                document = await self.store.upsert_document(document)
            artifacts = await self.store.list_artifacts(key)
            by_target: defaultdict[str, list[Artifact]] = defaultdict(list)
            for artifact in artifacts:
                by_target[artifact.target].append(artifact)

            target_names = sorted(set(self.connectors) | set(by_target))
            results = await asyncio.gather(
                *[
                    self._reconcile_target(
                        target,
                        document,
                        by_target[target],
                        mutate,
                    )
                    for target in target_names
                ]
            )
            status = (
                VerificationStatus.VERIFIED
                if results and all(result.clean for result in results)
                else VerificationStatus.FAILED
            )
            receipt = Receipt(
                receipt_id=str(uuid4()),
                tenant_id=document.tenant_id,
                document_id=document.document_id,
                document_version=document.version,
                desired_state=document.desired_state.value,
                status=status,
                checked_at=utcnow(),
                targets=results,
                deletion_mode=(
                    document.deletion_mode.value if document.deletion_mode is not None else None
                ),
                purge_after=document.purge_after,
            )
            receipt.signature = self.signer.sign(receipt)
            return await self.store.save_receipt(receipt)

    async def reconcile_all(self) -> list[Receipt]:
        documents = await self.store.list_documents()
        return await asyncio.gather(*[self.reconcile(document.key) for document in documents])

    async def _reconcile_target(
        self,
        target: str,
        document: Document,
        artifacts: list[Artifact],
        mutate: bool,
    ) -> TargetResult:
        connector = self.connectors.get(target)
        if connector is None:
            message = f"no connector configured for registered target {target}"
            await self.store.mark_artifacts(document.key, target, ArtifactState.ERROR, message)
            return TargetResult(target=target, clean=False, error=message)

        try:
            deleted_count = 0
            if mutate:
                if document.desired_state == DesiredState.DELETED:
                    deleted_count = await connector.delete(document, artifacts)
                else:
                    await connector.apply_permissions(document, artifacts)

            discovered = await connector.discover(document)
            clean = (
                not discovered
                if document.desired_state == DesiredState.DELETED
                else self._acl_clean(discovered, document.allowed_principals)
            )
            await self.store.mark_artifacts(
                document.key,
                target,
                ArtifactState.DELETED
                if clean and document.desired_state == DesiredState.DELETED
                else ArtifactState.PRESENT,
                None if clean else "verification found stale records",
            )
            return TargetResult(
                target=target,
                clean=clean,
                deleted_count=deleted_count,
                remaining_count=len(discovered) if not clean else 0,
                discovered_count=len(discovered),
            )
        except Exception as exc:  # connector boundaries must become auditable failures
            message = f"{type(exc).__name__}: {exc}"
            await self.store.mark_artifacts(document.key, target, ArtifactState.ERROR, message)
            return TargetResult(target=target, clean=False, error=message)

    @staticmethod
    def _acl_clean(records: list[dict[str, object]], expected: tuple[str, ...]) -> bool:
        wanted = sorted(expected)
        for record in records:
            payload = record.get("payload")
            source = payload if isinstance(payload, dict) else record
            actual = source.get("allowed_principals")
            if actual is None or sorted(str(value) for value in actual) != wanted:  # type: ignore[union-attr]
                return False
        return True

    async def _get_document(self, key: DocumentKey) -> Document:
        document = await self.store.get_document(key)
        if not document:
            raise NotFoundError(f"document {key.tenant_id}/{key.document_id} not found")
        return document
