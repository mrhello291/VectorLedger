from __future__ import annotations

import json
import os
import time

import httpx
import psycopg
import redis

API = os.environ.get("VL_API_URL", "http://localhost:8080")
POSTGRES = os.environ.get(
    "VL_TARGET_POSTGRES_URL", "postgresql://vectorledger:vectorledger@localhost:5432/vectorledger"
)
QDRANT = os.environ.get("VL_QDRANT_URL", "http://localhost:6333")
REDIS = os.environ.get("VL_REDIS_URL", "redis://localhost:6379/0")
HEADERS = {"X-Tenant-ID": "acme"}
IMMEDIATE_DOCUMENT = "salary-policy"
SCHEDULED_DOCUMENT = "benefits-handbook"


def wait_for_api() -> None:
    for _ in range(60):
        try:
            if httpx.get(f"{API}/healthz", timeout=1).is_success:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("VectorLedger API did not become ready")


def seed_target(
    document_id: str,
    chunk_id: str,
    point_id: int,
    body: str,
    principal: str,
) -> None:
    with psycopg.connect(POSTGRES) as connection:
        connection.execute(
            """INSERT INTO rag_chunks
               (chunk_id, tenant_id, document_id, body, allowed_principals)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (chunk_id) DO UPDATE SET body = EXCLUDED.body""",
            (
                chunk_id,
                "acme",
                document_id,
                body,
                [principal],
            ),
        )

    collection = httpx.put(
        f"{QDRANT}/collections/rag_chunks",
        json={"vectors": {"size": 4, "distance": "Cosine"}},
        timeout=10,
    )
    if collection.status_code != 409:
        collection.raise_for_status()
    httpx.put(
        f"{QDRANT}/collections/rag_chunks/points?wait=true",
        json={
            "points": [
                {
                    "id": point_id,
                    "vector": [0.1, 0.2, 0.3, 0.4],
                    "payload": {
                        "tenant_id": "acme",
                        "document_id": document_id,
                        "allowed_principals": [principal],
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()
    redis.Redis.from_url(REDIS).set(
        f"vl:acme:{document_id}:answer:123",
        f"Cached answer for {document_id}",
    )


def register_document(document_id: str, version: int, principal: str) -> None:
    response = httpx.post(
        f"{API}/v1/documents",
        headers=HEADERS,
        json={
            "document_id": document_id,
            "version": version,
            "source_uri": f"s3://acme-private/{document_id}.pdf",
            "allowed_principals": [principal],
        },
        timeout=10,
    )
    response.raise_for_status()


def main() -> None:
    wait_for_api()
    version = int(time.time())
    principal = "employee:alice"

    seed_target(
        IMMEDIATE_DOCUMENT,
        "chunk-immediate",
        1,
        "Salary bands are...",
        principal,
    )
    seed_target(
        SCHEDULED_DOCUMENT,
        "chunk-scheduled",
        2,
        "Benefits policy is...",
        principal,
    )
    register_document(IMMEDIATE_DOCUMENT, version, principal)
    register_document(SCHEDULED_DOCUMENT, version, principal)
    print("Seeded two documents across PostgreSQL, Qdrant, and Redis.")
    print("No artifacts were registered: discovery relies on stable metadata.")

    deleted = httpx.post(
        f"{API}/v1/documents/{IMMEDIATE_DOCUMENT}/delete",
        headers=HEADERS,
        json={"version": version + 1, "mode": "immediate"},
        timeout=30,
    )
    deleted.raise_for_status()
    print("\nImmediate-deletion receipt:\n")
    print(json.dumps(deleted.json(), indent=2))

    scheduled = httpx.post(
        f"{API}/v1/documents/{SCHEDULED_DOCUMENT}/delete",
        headers=HEADERS,
        json={
            "version": version + 1,
            "mode": "scheduled",
            "grace_period_seconds": 259_200,
        },
        timeout=30,
    )
    scheduled.raise_for_status()
    print("\nScheduled-deletion quarantine receipt:\n")
    print(json.dumps(scheduled.json(), indent=2))

    restored = httpx.post(
        f"{API}/v1/documents/{SCHEDULED_DOCUMENT}/restore",
        headers=HEADERS,
        json={"version": version + 2, "allowed_principals": [principal]},
        timeout=30,
    )
    restored.raise_for_status()
    print("\nRestoration result (chunks reused, cache will regenerate):\n")
    print(json.dumps(restored.json(), indent=2))


if __name__ == "__main__":
    main()
