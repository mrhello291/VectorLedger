from __future__ import annotations

import json

import httpx
import pytest

from vectorledger.connectors.qdrant import QdrantConnector
from vectorledger.models import Document


@pytest.mark.asyncio
async def test_discover_follows_pages_and_deduplicates_points() -> None:
    offsets: list[object] = []
    pages = iter(
        [
            {"points": [{"id": 1}, {"id": 2}], "next_page_offset": 2},
            {"points": [{"id": 2}, {"id": 3}], "next_page_offset": 3},
            {"points": [{"id": 4}]},
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        offsets.append(body.get("offset"))
        return httpx.Response(200, json={"result": next(pages)})

    connector = QdrantConnector("http://qdrant", "chunks")
    await connector.client.aclose()
    connector.client = httpx.AsyncClient(
        base_url="http://qdrant", transport=httpx.MockTransport(handler)
    )
    try:
        document = Document("acme", "handbook", 1, "s3://acme/handbook.pdf")
        points = await connector.discover(document)
    finally:
        await connector.close()

    assert offsets == [None, 2, 3]
    assert [point["id"] for point in points] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_discover_returns_empty_for_empty_final_page() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": {"points": []}})

    connector = QdrantConnector("http://qdrant", "chunks", timeout=10.0)
    await connector.client.aclose()
    connector.client = httpx.AsyncClient(
        base_url="http://qdrant", transport=httpx.MockTransport(handler)
    )
    try:
        points = await connector.discover(Document("acme", "handbook", 1, "s3://doc"))
    finally:
        await connector.close()

    assert points == []


@pytest.mark.asyncio
async def test_discover_rejects_repeated_page_offset() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"result": {"points": [], "next_page_offset": "same-offset"}},
        )

    connector = QdrantConnector("http://qdrant", "chunks")
    await connector.client.aclose()
    connector.client = httpx.AsyncClient(
        base_url="http://qdrant", transport=httpx.MockTransport(handler)
    )
    try:
        with pytest.raises(RuntimeError, match="repeated scroll offset"):
            await connector.discover(Document("acme", "handbook", 1, "s3://doc"))
    finally:
        await connector.close()
