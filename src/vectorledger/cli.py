from __future__ import annotations

import json
from typing import Annotated

import httpx
import typer
import uvicorn

from vectorledger.models import DeletionMode

app = typer.Typer(help="VectorLedger RAG consistency controller")


def _headers(tenant: str, api_key: str | None) -> dict[str, str]:
    headers = {"X-Tenant-ID": tenant}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _print_response(response: httpx.Response) -> None:
    if response.is_error:
        typer.echo(response.text, err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(response.json(), indent=2, default=str))


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
) -> None:
    """Run the API and anti-entropy worker."""
    uvicorn.run("vectorledger.api:app", host=host, port=port, reload=reload)


@app.command("delete")
def delete_document(
    document_id: str,
    tenant: Annotated[str, typer.Option("--tenant", "-t")],
    url: str = "http://localhost:8080",
    api_key: str | None = None,
    mode: DeletionMode = DeletionMode.IMMEDIATE,
    grace_period_seconds: int | None = None,
) -> None:
    """Immediately delete or quarantine and schedule a document deletion."""
    response = httpx.post(
        f"{url}/v1/documents/{document_id}/delete",
        headers=_headers(tenant, api_key),
        json={"mode": mode.value, "grace_period_seconds": grace_period_seconds},
        timeout=60,
    )
    _print_response(response)


@app.command("restore")
def restore_document(
    document_id: str,
    tenant: Annotated[str, typer.Option("--tenant", "-t")],
    principal: Annotated[list[str], typer.Option("--principal", "-p")],
    url: str = "http://localhost:8080",
    api_key: str | None = None,
) -> None:
    """Cancel scheduled deletion or reactivate a hard-deleted document."""
    response = httpx.post(
        f"{url}/v1/documents/{document_id}/restore",
        headers=_headers(tenant, api_key),
        json={"allowed_principals": principal},
        timeout=60,
    )
    _print_response(response)


@app.command()
def verify(
    document_id: str,
    tenant: Annotated[str, typer.Option("--tenant", "-t")],
    url: str = "http://localhost:8080",
    api_key: str | None = None,
) -> None:
    """Verify the current desired state without mutating a target."""
    response = httpx.get(
        f"{url}/v1/documents/{document_id}/verify",
        headers=_headers(tenant, api_key),
        timeout=60,
    )
    _print_response(response)


@app.command()
def reconcile(
    document_id: str,
    tenant: Annotated[str, typer.Option("--tenant", "-t")],
    url: str = "http://localhost:8080",
    api_key: str | None = None,
) -> None:
    """Repair a document's target state and issue a receipt."""
    response = httpx.post(
        f"{url}/v1/documents/{document_id}/reconcile",
        headers=_headers(tenant, api_key),
        timeout=60,
    )
    _print_response(response)


if __name__ == "__main__":
    app()
