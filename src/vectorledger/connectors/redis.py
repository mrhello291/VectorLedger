from __future__ import annotations

from redis.asyncio import Redis

from vectorledger.models import Artifact, Document


class RedisConnector:
    name = "redis"

    def __init__(self, url: str, key_prefix: str = "vl") -> None:
        self.client = Redis.from_url(url, decode_responses=True)
        self.key_prefix = key_prefix

    def _pattern(self, document: Document) -> str:
        return f"{self.key_prefix}:{document.tenant_id}:{document.document_id}:*"

    async def _keys(self, document: Document) -> list[str]:
        return [
            key async for key in self.client.scan_iter(match=self._pattern(document), count=200)
        ]

    async def delete(self, document: Document, artifacts: list[Artifact]) -> int:
        keys = await self._keys(document)
        return int(await self.client.delete(*keys)) if keys else 0

    async def apply_permissions(self, document: Document, artifacts: list[Artifact]) -> int:
        # Cached answers cannot safely be rewritten when access changes; invalidate them.
        return await self.delete(document, artifacts)

    async def discover(self, document: Document) -> list[dict[str, object]]:
        return [{"key": key} for key in await self._keys(document)]

    async def close(self) -> None:
        await self.client.close()
