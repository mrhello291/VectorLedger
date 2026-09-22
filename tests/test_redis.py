from __future__ import annotations

import pytest

from vectorledger.connectors.redis import RedisConnector
from vectorledger.models import Document


@pytest.mark.asyncio
async def test_namespace_encodes_glob_and_separator_characters() -> None:
    connector = RedisConnector("redis://localhost:6379/0")
    try:
        document = Document(
            tenant_id="acme:*",
            document_id=r"policy?[draft]\\finance",
            version=1,
            source_uri="s3://acme/policy.pdf",
        )

        assert connector._pattern(document) == ("vl:acme%3A%2A:policy%3F%5Bdraft%5D%5C%5Cfinance:*")
    finally:
        await connector.close()


def test_rejects_unsafe_key_prefix() -> None:
    with pytest.raises(ValueError, match="key prefix"):
        RedisConnector("redis://localhost:6379/0", key_prefix="vl:*")
