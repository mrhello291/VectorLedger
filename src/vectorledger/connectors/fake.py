from __future__ import annotations

from vectorledger.models import Artifact, Document


class FakeConnector:
    def __init__(
        self,
        name: str,
        records: list[dict[str, object]] | None = None,
        invalidate_on_permissions: bool = False,
    ) -> None:
        self.name = name
        self.records = records or []
        self.invalidate_on_permissions = invalidate_on_permissions
        self.fail_delete = False
        self.delete_calls = 0
        self.permission_calls = 0

    def _matches(self, document: Document, record: dict[str, object]) -> bool:
        return (
            record.get("tenant_id") == document.tenant_id
            and record.get("document_id") == document.document_id
        )

    async def delete(self, document: Document, artifacts: list[Artifact]) -> int:
        self.delete_calls += 1
        if self.fail_delete:
            raise RuntimeError("injected connector failure")
        before = len(self.records)
        self.records = [record for record in self.records if not self._matches(document, record)]
        return before - len(self.records)

    async def apply_permissions(self, document: Document, artifacts: list[Artifact]) -> int:
        self.permission_calls += 1
        if self.invalidate_on_permissions:
            return await self.delete(document, artifacts)
        updated = 0
        for record in self.records:
            if self._matches(document, record):
                record["allowed_principals"] = list(document.allowed_principals)
                updated += 1
        return updated

    async def discover(self, document: Document) -> list[dict[str, object]]:
        return [dict(record) for record in self.records if self._matches(document, record)]
