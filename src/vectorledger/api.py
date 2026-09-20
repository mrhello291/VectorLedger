import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from vectorledger.config import Settings
from vectorledger.connectors.base import Connector
from vectorledger.connectors.postgres import PostgresConnector
from vectorledger.connectors.qdrant import QdrantConnector
from vectorledger.connectors.redis import RedisConnector
from vectorledger.models import Artifact, Document, DocumentKey
from vectorledger.receipts import ReceiptSigner
from vectorledger.service import NotFoundError, VectorLedgerService
from vectorledger.store.postgres import PostgresStore
from vectorledger.worker import anti_entropy_loop


class DocumentInput(BaseModel):
    document_id: str = Field(min_length=1, max_length=256)
    version: int = Field(ge=1)
    source_uri: str = Field(min_length=1, max_length=2048)
    content_hash: str | None = Field(default=None, max_length=256)
    allowed_principals: list[str] = Field(default_factory=list)


class ArtifactInput(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=512)
    document_version: int = Field(ge=1)
    target: str = Field(min_length=1, max_length=128)
    locator: dict[str, object] = Field(default_factory=dict)


class DeleteInput(BaseModel):
    version: int | None = Field(default=None, ge=1)


class PermissionInput(BaseModel):
    allowed_principals: list[str]
    version: int | None = Field(default=None, ge=1)


def _connectors(settings: Settings) -> dict[str, Connector]:
    connectors: dict[str, Connector] = {}
    if settings.qdrant_url:
        connectors["qdrant"] = QdrantConnector(
            settings.qdrant_url,
            settings.qdrant_collection,
            settings.qdrant_api_key,
        )
    if settings.redis_url:
        connectors["redis"] = RedisConnector(settings.redis_url)
    if settings.target_postgres_url:
        connectors["postgres"] = PostgresConnector(
            settings.target_postgres_url,
            settings.target_postgres_table,
        )
    return connectors


def create_app(
    settings: Settings | None = None,
    service: VectorLedgerService | None = None,
) -> FastAPI:
    config = settings or Settings()
    owns_service = service is None
    if service is None:
        store = PostgresStore(config.database_url)
        service = VectorLedgerService(
            store, _connectors(config), ReceiptSigner(config.receipt_secret)
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        assert service is not None
        await service.store.initialize()
        stop = asyncio.Event()
        worker = asyncio.create_task(
            anti_entropy_loop(service, config.reconcile_interval_seconds, stop),
            name="vectorledger-anti-entropy",
        )
        app.state.service = service
        try:
            yield
        finally:
            stop.set()
            await worker
            if owns_service:
                for connector in service.connectors.values():
                    close = getattr(connector, "close", None)
                    if close:
                        await close()
                await service.store.close()

    app = FastAPI(
        title="VectorLedger",
        version="0.1.0",
        description="Reconciliation and deletion verification for RAG data stores.",
        lifespan=lifespan,
    )

    async def authenticate(
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> None:
        if config.api_key and x_api_key != config.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    async def get_service(request: Request) -> VectorLedgerService:
        return request.app.state.service  # type: ignore[no-any-return]

    Tenant = Annotated[str, Header(alias="X-Tenant-ID", min_length=1, max_length=256)]
    Service = Annotated[VectorLedgerService, Depends(get_service)]

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/healthz", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/documents", status_code=201, dependencies=[Depends(authenticate)])
    async def register_document(
        body: DocumentInput, tenant_id: Tenant, svc: Service
    ) -> dict[str, object]:
        document = await svc.register_document(
            Document(
                tenant_id=tenant_id,
                document_id=body.document_id,
                version=body.version,
                source_uri=body.source_uri,
                content_hash=body.content_hash,
                allowed_principals=tuple(body.allowed_principals),
            )
        )
        return asdict(document)

    @app.post(
        "/v1/documents/{document_id}/artifacts",
        status_code=201,
        dependencies=[Depends(authenticate)],
    )
    async def register_artifact(
        document_id: str, body: ArtifactInput, tenant_id: Tenant, svc: Service
    ) -> dict[str, object]:
        artifact = await svc.register_artifact(
            Artifact(
                artifact_id=body.artifact_id,
                tenant_id=tenant_id,
                document_id=document_id,
                document_version=body.document_version,
                target=body.target,
                locator=body.locator,
            )
        )
        return asdict(artifact)

    @app.post("/v1/documents/{document_id}/delete", dependencies=[Depends(authenticate)])
    async def delete_document(
        document_id: str, body: DeleteInput, tenant_id: Tenant, svc: Service
    ) -> dict[str, object]:
        return (
            await svc.request_deletion(DocumentKey(tenant_id, document_id), body.version)
        ).as_dict()

    @app.put("/v1/documents/{document_id}/permissions", dependencies=[Depends(authenticate)])
    async def update_permissions(
        document_id: str, body: PermissionInput, tenant_id: Tenant, svc: Service
    ) -> dict[str, object]:
        return (
            await svc.change_permissions(
                DocumentKey(tenant_id, document_id), tuple(body.allowed_principals), body.version
            )
        ).as_dict()

    @app.post("/v1/documents/{document_id}/reconcile", dependencies=[Depends(authenticate)])
    async def reconcile(document_id: str, tenant_id: Tenant, svc: Service) -> dict[str, object]:
        return (await svc.reconcile(DocumentKey(tenant_id, document_id))).as_dict()

    @app.get("/v1/documents/{document_id}/verify", dependencies=[Depends(authenticate)])
    async def verify(document_id: str, tenant_id: Tenant, svc: Service) -> dict[str, object]:
        return (await svc.verify(DocumentKey(tenant_id, document_id))).as_dict()

    @app.get("/v1/receipts/{receipt_id}", dependencies=[Depends(authenticate)])
    async def receipt(receipt_id: str, svc: Service) -> dict[str, object]:
        value = await svc.store.get_receipt(receipt_id)
        if not value:
            raise HTTPException(status_code=404, detail="receipt not found")
        return value.as_dict()

    return app


app = create_app()
