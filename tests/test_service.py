from __future__ import annotations

import unittest

from vectorledger.connectors.fake import FakeConnector
from vectorledger.models import (
    Artifact,
    ArtifactState,
    DesiredState,
    Document,
    DocumentKey,
    Receipt,
    TargetResult,
    VerificationStatus,
    utcnow,
)
from vectorledger.receipts import ReceiptSigner
from vectorledger.service import NotFoundError, VectorLedgerService
from vectorledger.store.memory import MemoryStore


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.store = MemoryStore()
        self.qdrant = FakeConnector(
            "qdrant",
            [
                {
                    "id": "vector-1",
                    "tenant_id": "acme",
                    "document_id": "handbook",
                    "allowed_principals": ["team:all"],
                }
            ],
        )
        self.redis = FakeConnector(
            "redis",
            [{"key": "cache-1", "tenant_id": "acme", "document_id": "handbook"}],
            invalidate_on_permissions=True,
        )
        self.signer = ReceiptSigner("a-secret-long-enough-for-tests")
        self.service = VectorLedgerService(
            self.store,
            {"qdrant": self.qdrant, "redis": self.redis},
            self.signer,
        )
        await self.service.register_document(
            Document(
                tenant_id="acme",
                document_id="handbook",
                version=1,
                source_uri="s3://acme/handbook.pdf",
                allowed_principals=("team:all",),
            )
        )

    async def test_deletion_cleans_all_targets_and_signs_receipt(self) -> None:
        receipt = await self.service.request_deletion(DocumentKey("acme", "handbook"))

        self.assertEqual(receipt.status, VerificationStatus.VERIFIED)
        self.assertTrue(all(result.clean for result in receipt.targets))
        self.assertEqual(self.qdrant.records, [])
        self.assertEqual(self.redis.records, [])
        self.assertTrue(self.signer.verify(receipt))

    async def test_deletion_is_idempotent(self) -> None:
        await self.service.request_deletion(DocumentKey("acme", "handbook"))
        second = await self.service.reconcile(DocumentKey("acme", "handbook"))

        self.assertEqual(second.status, VerificationStatus.VERIFIED)
        self.assertEqual(sum(result.deleted_count for result in second.targets), 0)

    async def test_discovers_unregistered_records(self) -> None:
        # No lineage artifacts are registered, but metadata discovery still finds
        # and deletes both records.
        receipt = await self.service.request_deletion(DocumentKey("acme", "handbook"))

        qdrant = next(result for result in receipt.targets if result.target == "qdrant")
        self.assertEqual(qdrant.deleted_count, 1)
        self.assertTrue(qdrant.clean)

    async def test_partial_failure_never_produces_verified_receipt(self) -> None:
        self.qdrant.fail_delete = True
        receipt = await self.service.request_deletion(DocumentKey("acme", "handbook"))

        self.assertEqual(receipt.status, VerificationStatus.FAILED)
        qdrant = next(result for result in receipt.targets if result.target == "qdrant")
        self.assertIn("injected connector failure", qdrant.error or "")
        self.assertTrue(self.signer.verify(receipt))

    async def test_retry_repairs_a_previous_failure(self) -> None:
        self.qdrant.fail_delete = True
        first = await self.service.request_deletion(DocumentKey("acme", "handbook"))
        self.qdrant.fail_delete = False
        second = await self.service.reconcile(DocumentKey("acme", "handbook"))

        self.assertEqual(first.status, VerificationStatus.FAILED)
        self.assertEqual(second.status, VerificationStatus.VERIFIED)

    async def test_permission_change_is_propagated(self) -> None:
        receipt = await self.service.change_permissions(
            DocumentKey("acme", "handbook"), ("team:hr",)
        )

        self.assertEqual(receipt.status, VerificationStatus.VERIFIED)
        self.assertEqual(self.qdrant.records[0]["allowed_principals"], ["team:hr"])
        self.assertEqual(self.redis.records, [])

    async def test_registered_target_without_connector_is_failure(self) -> None:
        await self.service.register_artifact(
            Artifact(
                artifact_id="unknown-1",
                tenant_id="acme",
                document_id="handbook",
                document_version=1,
                target="missing",
                locator={"id": "1"},
            )
        )
        receipt = await self.service.request_deletion(DocumentKey("acme", "handbook"))

        self.assertEqual(receipt.status, VerificationStatus.FAILED)
        artifacts = await self.store.list_artifacts(DocumentKey("acme", "handbook"))
        self.assertEqual(artifacts[0].state, ArtifactState.ERROR)

    async def test_verify_does_not_mutate_target(self) -> None:
        document = await self.store.get_document(DocumentKey("acme", "handbook"))
        assert document is not None
        document.desired_state = DesiredState.DELETED
        await self.store.upsert_document(document)

        receipt = await self.service.verify(DocumentKey("acme", "handbook"))

        self.assertEqual(receipt.status, VerificationStatus.FAILED)
        self.assertEqual(self.qdrant.delete_calls, 0)

    async def test_cannot_register_artifact_for_unknown_document(self) -> None:
        with self.assertRaises(NotFoundError):
            await self.service.register_artifact(
                Artifact("x", "acme", "unknown", 1, "qdrant", {"id": "x"})
            )

    async def test_document_version_cannot_move_backwards(self) -> None:
        with self.assertRaises(ValueError):
            await self.service.register_document(
                Document("acme", "handbook", 0, "s3://acme/old.pdf")
            )


class ReceiptSignerTests(unittest.TestCase):
    def test_tampering_invalidates_signature(self) -> None:
        signer = ReceiptSigner("a-secret-long-enough-for-tests")
        receipt = Receipt(
            receipt_id="r1",
            tenant_id="acme",
            document_id="doc",
            document_version=1,
            desired_state="deleted",
            status=VerificationStatus.VERIFIED,
            checked_at=utcnow(),
            targets=[TargetResult(target="qdrant", clean=True)],
        )
        receipt.signature = signer.sign(receipt)
        self.assertTrue(signer.verify(receipt))
        receipt.document_version = 2
        self.assertFalse(signer.verify(receipt))

    def test_rejects_short_secret(self) -> None:
        with self.assertRaises(ValueError):
            ReceiptSigner("short")


if __name__ == "__main__":
    unittest.main()
