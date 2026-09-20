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
        points: list[dict[str, object]] = []
        seen_ids: set[object] = set()
        seen_offsets: set[object] = set()
        offset: object | None = None

        while True:
            request: dict[str, object] = {
                "filter": self._filter(document),
                "limit": 256,
                "with_payload": True,
            }
            if offset is not None:
                request["offset"] = offset

            response = await self.client.post(
                f"/collections/{self.collection}/points/scroll",
                json=request,
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            for point in result.get("points", []):
                point_id = point["id"]
                if point_id not in seen_ids:
                    seen_ids.add(point_id)
                    points.append({"id": point_id, "payload": point.get("payload", {})})

            next_offset = result.get("next_page_offset")
            if next_offset is None:
                return points
            if next_offset in seen_offsets:
                raise RuntimeError(f"Qdrant repeated scroll offset {next_offset!r}")

            seen_offsets.add(next_offset)
            offset = next_offset

    async def close(self) -> None:
        await self.client.aclose()
