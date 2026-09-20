"""Instrument a LangChain ingestion pipeline without replacing it."""

from __future__ import annotations

from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from vectorledger.sdk import VectorLedgerClient

TENANT_ID = "acme"
SOURCE_URI = "s3://acme-private/salary-policy.txt"
DOCUMENT_ID = str(uuid5(NAMESPACE_URL, SOURCE_URI))
VERSION = 1


def add_to_your_vector_store(chunks: list[Document]) -> list[str]:
    """Replace with Qdrant, pgvector, Azure AI Search, or another vector store."""
    return [f"point-{index}" for index, _ in enumerate(chunks)]


def main() -> None:
    text = "Salary policy example text loaded by the company's existing source connector."
    splitter = RecursiveCharacterTextSplitter(chunk_size=120, chunk_overlap=20)
    chunks = splitter.create_documents([text])

    lineage = {
        "tenant_id": TENANT_ID,
        "document_id": DOCUMENT_ID,
        "document_version": VERSION,
        "source_uri": SOURCE_URI,
    }
    for chunk in chunks:
        chunk.metadata.update(lineage)

    with VectorLedgerClient("http://localhost:8080", TENANT_ID) as ledger:
        ledger.register_document(
            DOCUMENT_ID,
            VERSION,
            SOURCE_URI,
            allowed_principals=["group:hr"],
            content_hash=f"sha256:{sha256(text.encode()).hexdigest()}",
        )
        point_ids = add_to_your_vector_store(chunks)
        for point_id in point_ids:
            ledger.register_artifact(
                DOCUMENT_ID,
                artifact_id=f"qdrant:rag_chunks:{point_id}",
                document_version=VERSION,
                target="qdrant",
                locator={"collection": "rag_chunks", "point_id": point_id},
            )

    print(f"Tracked {len(chunks)} chunks for {DOCUMENT_ID}")


if __name__ == "__main__":
    main()
