from __future__ import annotations

from typing import Protocol

from vectorledger.models import Artifact, Document


class Connector(Protocol):
    """A target adapter. Every operation must be safe to repeat."""

    name: str

    async def delete(self, document: Document, artifacts: list[Artifact]) -> int: ...

    async def apply_permissions(self, document: Document, artifacts: list[Artifact]) -> int: ...

    async def discover(self, document: Document) -> list[dict[str, object]]: ...


class ConnectorError(RuntimeError):
    pass
