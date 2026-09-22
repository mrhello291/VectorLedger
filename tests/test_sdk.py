from __future__ import annotations

import json

import httpx

from vectorledger.sdk import VectorLedgerClient


def test_registers_document_with_tenant_and_api_key() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed.update(
            method=request.method,
            path=request.url.path,
            tenant=request.headers["X-Tenant-ID"],
            api_key=request.headers["X-API-Key"],
            body=json.loads(request.content),
        )
        return httpx.Response(201, json={"document_id": "doc-1"})

    with VectorLedgerClient(
        "http://vectorledger",
        "acme",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.register_document(
            "doc-1", 1, "s3://acme/doc.pdf", ["group:finance"], "sha256:abc"
        )

    assert result == {"document_id": "doc-1"}
    assert observed == {
        "method": "POST",
        "path": "/v1/documents",
        "tenant": "acme",
        "api_key": "secret",
        "body": {
            "document_id": "doc-1",
            "version": 1,
            "source_uri": "s3://acme/doc.pdf",
            "content_hash": "sha256:abc",
            "allowed_principals": ["group:finance"],
        },
    }


def test_registers_artifact_and_verifies() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"status": "verified"})

    with VectorLedgerClient(
        "http://vectorledger", "acme", transport=httpx.MockTransport(handler)
    ) as client:
        client.register_artifact("doc-1", "qdrant:1", 1, "qdrant", {"point_id": 1})
        result = client.verify("doc-1")

    assert paths == ["/v1/documents/doc-1/artifacts", "/v1/documents/doc-1/verify"]
    assert result["status"] == "verified"


def test_schedules_deletion_and_restores_authoritative_acl() -> None:
    observed: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"status": "verified"})

    with VectorLedgerClient(
        "http://vectorledger", "acme", transport=httpx.MockTransport(handler)
    ) as client:
        client.delete_document("doc-1", version=4, mode="scheduled", grace_period_seconds=259200)
        client.restore_document("doc-1", ["group:hr"], version=5)

    assert observed == [
        (
            "POST",
            "/v1/documents/doc-1/delete",
            {
                "version": 4,
                "mode": "scheduled",
                "grace_period_seconds": 259200,
            },
        ),
        (
            "POST",
            "/v1/documents/doc-1/restore",
            {"allowed_principals": ["group:hr"], "version": 5},
        ),
    ]
