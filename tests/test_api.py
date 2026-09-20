from __future__ import annotations

import httpx
import pytest

from vectorledger.api import create_app
from vectorledger.config import Settings
from vectorledger.connectors.fake import FakeConnector
from vectorledger.receipts import ReceiptSigner
from vectorledger.service import VectorLedgerService
from vectorledger.store.memory import MemoryStore


@pytest.mark.asyncio
async def test_document_deletion_workflow_over_http() -> None:
    connector = FakeConnector("qdrant", [{"id": "v1", "tenant_id": "acme", "document_id": "doc-1"}])
    service = VectorLedgerService(
        MemoryStore(), {"qdrant": connector}, ReceiptSigner("a-secret-long-enough-for-tests")
    )
    app = create_app(Settings(api_key="test-key", reconcile_interval_seconds=3600), service)
    transport = httpx.ASGITransport(app=app)

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        unauthorized = await client.post(
            "/v1/documents",
            headers={"X-Tenant-ID": "acme"},
            json={"document_id": "doc-1", "version": 1, "source_uri": "s3://acme/doc.pdf"},
        )
        assert unauthorized.status_code == 401

        headers = {"X-Tenant-ID": "acme", "X-API-Key": "test-key"}
        created = await client.post(
            "/v1/documents",
            headers=headers,
            json={"document_id": "doc-1", "version": 1, "source_uri": "s3://acme/doc.pdf"},
        )
        assert created.status_code == 201

        deleted = await client.post("/v1/documents/doc-1/delete", headers=headers, json={})
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "verified"
        assert connector.records == []


@pytest.mark.asyncio
async def test_tenant_header_is_required() -> None:
    service = VectorLedgerService(
        MemoryStore(), {}, ReceiptSigner("a-secret-long-enough-for-tests")
    )
    app = create_app(Settings(reconcile_interval_seconds=3600), service)
    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.post(
            "/v1/documents",
            json={"document_id": "doc-1", "version": 1, "source_uri": "file:///doc.pdf"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_scheduled_deletion_can_be_restored_without_reingestion() -> None:
    connector = FakeConnector(
        "qdrant",
        [
            {
                "id": "v1",
                "tenant_id": "acme",
                "document_id": "doc-1",
                "allowed_principals": ["team:all"],
            }
        ],
    )
    service = VectorLedgerService(
        MemoryStore(), {"qdrant": connector}, ReceiptSigner("a-secret-long-enough-for-tests")
    )
    app = create_app(Settings(reconcile_interval_seconds=3600), service)
    transport = httpx.ASGITransport(app=app)

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        headers = {"X-Tenant-ID": "acme"}
        await client.post(
            "/v1/documents",
            headers=headers,
            json={
                "document_id": "doc-1",
                "version": 1,
                "source_uri": "s3://acme/doc.pdf",
                "allowed_principals": ["team:all"],
            },
        )

        scheduled = await client.post(
            "/v1/documents/doc-1/delete",
            headers=headers,
            json={"mode": "scheduled", "grace_period_seconds": 172800},
        )
        assert scheduled.status_code == 200
        assert scheduled.json()["desired_state"] == "pending_deletion"
        assert connector.records[0]["allowed_principals"] == []

        restored = await client.post(
            "/v1/documents/doc-1/restore",
            headers=headers,
            json={"allowed_principals": ["team:all"]},
        )
        assert restored.status_code == 200
        assert restored.json()["reingestion_required"] is False
        assert connector.records[0]["allowed_principals"] == ["team:all"]
