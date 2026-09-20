from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


class DesiredState(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class ArtifactState(StrEnum):
    PRESENT = "present"
    DELETED = "deleted"
    ERROR = "error"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentKey:
    tenant_id: str
    document_id: str


@dataclass(slots=True)
class Document:
    tenant_id: str
    document_id: str
    version: int
    source_uri: str
    content_hash: str | None = None
    desired_state: DesiredState = DesiredState.ACTIVE
    allowed_principals: tuple[str, ...] = ()
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def key(self) -> DocumentKey:
        return DocumentKey(self.tenant_id, self.document_id)


@dataclass(slots=True)
class Artifact:
    artifact_id: str
    tenant_id: str
    document_id: str
    document_version: int
    target: str
    locator: dict[str, Any]
    state: ArtifactState = ArtifactState.PRESENT
    last_error: str | None = None
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class TargetResult:
    target: str
    clean: bool
    deleted_count: int = 0
    remaining_count: int = 0
    discovered_count: int = 0
    error: str | None = None


@dataclass(slots=True)
class Receipt:
    receipt_id: str
    tenant_id: str
    document_id: str
    document_version: int
    desired_state: str
    status: VerificationStatus
    checked_at: datetime
    targets: list[TargetResult]
    signature: str = ""

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("signature")
        value["checked_at"] = self.checked_at.isoformat()
        value["status"] = self.status.value
        return value

    def as_dict(self) -> dict[str, Any]:
        return {**self.payload(), "signature": self.signature}
