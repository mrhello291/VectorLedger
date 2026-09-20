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
DOCUMENT_ID = "salary-policy"


def wait_for_api() -> None:
    for _ in range(60):
        try:
            if httpx.get(f"{API}/healthz", timeout=1).is_success:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("VectorLedger API did not become ready")


def seed_targets() -> None:
    with psycopg.connect(POSTGRES) as connection:
        connection.execute(
            """INSERT INTO rag_chunks
               (chunk_id, tenant_id, document_id, body, allowed_principals)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (chunk_id) DO UPDATE SET body = EXCLUDED.body""",
            (
                "chunk-1",
                "acme",
                "salary-policy",
                "Salary bands are...",
                ["employee:alice"],
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
                    "id": 1,
                    "vector": [0.1, 0.2, 0.3, 0.4],
                    "payload": {
                        "tenant_id": "acme",
                        "document_id": "salary-policy",
                        "allowed_principals": ["employee:alice"],
                    },
                }
            ]
        },
        timeout=10,
    ).raise_for_status()
    redis.Redis.from_url(REDIS).set(
        "vl:acme:salary-policy:answer:123", "The salary band is confidential"
    )


def main() -> None:
    wait_for_api()
    seed_targets()
    version = int(time.time())

    created = httpx.post(
        f"{API}/v1/documents",
        headers=HEADERS,
        json={
            "document_id": DOCUMENT_ID,
            "version": version,
            "source_uri": "s3://acme-private/salary-policy.pdf",
            "allowed_principals": ["employee:alice"],
        },
        timeout=10,
    )
    created.raise_for_status()
    print("Seeded a document and derived data in PostgreSQL, Qdrant, and Redis.")
    print("No artifacts were registered: this demonstrates metadata discovery.")

    deleted = httpx.post(
        f"{API}/v1/documents/{DOCUMENT_ID}/delete",
        headers=HEADERS,
        json={"version": version + 1},
        timeout=30,
    )
    deleted.raise_for_status()
    print("\nDeletion receipt:\n")
    print(json.dumps(deleted.json(), indent=2))

    verified = httpx.get(f"{API}/v1/documents/{DOCUMENT_ID}/verify", headers=HEADERS, timeout=30)
    verified.raise_for_status()
    print("\nIndependent follow-up verification:\n")
    print(json.dumps(verified.json(), indent=2))


if __name__ == "__main__":
    main()
