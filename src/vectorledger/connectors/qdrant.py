from __future__ import annotations

from typing import Any

import httpx

from vectorledger.models import Artifact, Document


class QdrantConnector:
    name = "qdrant"

    def __init__(
        self,
        url: str,
        collection: str,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        headers = {"api-key": api_key} if api_key else {}
        self.client = httpx.AsyncClient(base_url=url.rstrip("/"), headers=headers, timeout=timeout)
        self.collection = collection

    def _filter(self, document: Document) -> dict[str, Any]:
        return {
            "must": [
                {"key": "tenant_id", "match": {"value": document.tenant_id}},
                {"key": "document_id", "match": {"value": document.document_id}},
            ]
        }

    async def delete(self, document: Document, artifacts: list[Artifact]) -> int:
        existing = await self.discover(document)
        response = await self.client.post(
            f"/collections/{self.collection}/points/delete",
            params={"wait": "true"},
            json={"filter": self._filter(document)},
        )
        response.raise_for_status()
        return len(existing)

    async def apply_permissions(self, document: Document, artifacts: list[Artifact]) -> int:
        response = await self.client.post(
            f"/collections/{self.collection}/points/payload",
            params={"wait": "true"},
            json={
                "payload": {"allowed_principals": list(document.allowed_principals)},
                "filter": self._filter(document),
            },
        )
        response.raise_for_status()
        return len(artifacts)

    async def discover(self, document: Document) -> list[dict[str, object]]:
        response = await self.client.post(
            f"/collections/{self.collection}/points/scroll",
            json={"filter": self._filter(document), "limit": 256, "with_payload": True},
        )
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        return [{"id": point["id"], "payload": point.get("payload", {})} for point in points]

    async def close(self) -> None:
        await self.client.aclose()
