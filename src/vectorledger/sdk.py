from __future__ import annotations

from typing import Any, cast

import httpx


class VectorLedgerClient:
    """Small synchronous client for instrumenting an existing ingestion pipeline."""

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"X-Tenant-ID": tenant_id}
        if api_key:
            headers["X-API-Key"] = api_key
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def register_document(
        self,
        document_id: str,
        version: int,
        source_uri: str,
        allowed_principals: list[str] | None = None,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/documents",
            json={
                "document_id": document_id,
                "version": version,
                "source_uri": source_uri,
                "content_hash": content_hash,
                "allowed_principals": allowed_principals or [],
            },
        )

    def register_artifact(
        self,
        document_id: str,
        artifact_id: str,
        document_version: int,
        target: str,
        locator: dict[str, object],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/documents/{document_id}/artifacts",
            json={
                "artifact_id": artifact_id,
                "document_version": document_version,
                "target": target,
                "locator": locator,
            },
        )

    def delete_document(
        self,
        document_id: str,
        version: int | None = None,
        mode: str = "immediate",
        grace_period_seconds: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/documents/{document_id}/delete",
            json={
                "version": version,
                "mode": mode,
                "grace_period_seconds": grace_period_seconds,
            },
        )

    def restore_document(
        self,
        document_id: str,
        allowed_principals: list[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/documents/{document_id}/restore",
            json={"allowed_principals": allowed_principals, "version": version},
        )

    def update_permissions(
        self,
        document_id: str,
        allowed_principals: list[str],
        version: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/v1/documents/{document_id}/permissions",
            json={"allowed_principals": allowed_principals, "version": version},
        )

    def verify(self, document_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/documents/{document_id}/verify")

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> VectorLedgerClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, path: str, json: object | None = None) -> dict[str, Any]:
        response = self.client.request(method, path, json=json)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
