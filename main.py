"""Neuron Service — standalone FastAPI memory hub.

Endpoints (all require X-API-Key header unless NEURON_API_KEY is empty):
  GET  /health
  GET  /api/neurons/status
  GET  /api/neurons/nodes
  POST /api/neurons/nodes
  POST /api/neurons/activate
  POST /api/neurons/strengthen
  POST /api/neurons/decay
  POST /api/neurons/sync-vault
  POST /api/neurons/remember
  DELETE /api/neurons/nodes/{node_id}
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from src import neuron_core as neurons
from src.vault_sync import sync_vault_notes

app = FastAPI(
    title="Neuron Service",
    description="Standalone neural memory hub — graph + FastEmbed + decay",
    version="1.0.0",
)

API_KEY = os.environ.get("NEURON_API_KEY", "")
VAULT_PATH = os.environ.get("NEURON_VAULT_PATH", "")


def _require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if not API_KEY:
        return  # auth disabled when key not set
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


# ── Request bodies ───────────────────────────────────────


class AddNodeBody(BaseModel):
    type: Literal["memory", "vault_note", "project", "session"] = "memory"
    label: str
    ref: str = ""
    base_weight: float = 0.5
    text: Optional[str] = None
    node_id: Optional[str] = None


class ActivateBody(BaseModel):
    query: str = ""
    node_ids: Optional[list[str]] = None
    top_k: int = Field(default=10, ge=1, le=50)


class StrengthenBody(BaseModel):
    ids: list[str]


class RememberBody(BaseModel):
    """Import a free-form fact into the graph as a memory node."""
    content: str
    source: str = "external"
    label: Optional[str] = None
    base_weight: float = 0.5
    pinned: bool = False


class SyncVaultBody(BaseModel):
    path: Optional[str] = None
    link_wikilinks: bool = True


# ── Routes ───────────────────────────────────────────────


@app.get("/health")
def health():
    return {"ok": True, "service": "neuron", "version": "1.0.0"}


@app.get("/api/neurons/status", dependencies=[Depends(_require_api_key)])
def api_status():
    return neurons.status()


@app.get("/api/neurons/nodes", dependencies=[Depends(_require_api_key)])
def api_list_nodes(include_archived: bool = False):
    return neurons.list_nodes(include_archived=include_archived)


@app.post("/api/neurons/nodes", dependencies=[Depends(_require_api_key)])
def api_add_node(body: AddNodeBody):
    return neurons.add_node(
        type=body.type,
        label=body.label,
        ref=body.ref or body.label,
        base_weight=body.base_weight,
        text=body.text,
        node_id=body.node_id,
    )


@app.post("/api/neurons/activate", dependencies=[Depends(_require_api_key)])
def api_activate(body: ActivateBody):
    return neurons.activate(
        query=body.query,
        node_ids=body.node_ids,
        top_k=body.top_k,
    )


@app.post("/api/neurons/strengthen", dependencies=[Depends(_require_api_key)])
def api_strengthen(body: StrengthenBody):
    return neurons.strengthen(body.ids)


@app.post("/api/neurons/decay", dependencies=[Depends(_require_api_key)])
def api_decay():
    return neurons.decay()


@app.post("/api/neurons/sync-vault", dependencies=[Depends(_require_api_key)])
def api_sync_vault(body: SyncVaultBody = SyncVaultBody()):
    path = body.path or VAULT_PATH
    if not path:
        raise HTTPException(
            status_code=400,
            detail="No vault path. Pass body.path or set NEURON_VAULT_PATH env.",
        )
    return sync_vault_notes(path, link_wikilinks=body.link_wikilinks)


@app.post("/api/neurons/remember", dependencies=[Depends(_require_api_key)])
def api_remember(body: RememberBody):
    """Accept a free-form fact from any agent (Hermes, Odys, etc.)."""
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    label = (body.label or content[:60]).strip()
    base = 0.9 if body.pinned else body.base_weight
    ref = f"{body.source}:{abs(hash(content)) % 10**10}"
    result = neurons.add_node(
        type="memory",
        label=label,
        ref=ref,
        base_weight=base,
        text=content,
    )
    return result


@app.post("/api/neurons/boot", dependencies=[Depends(_require_api_key)])
def api_boot():
    """Run natural_boot() on demand — re-seed vault + resync graph."""
    return neurons.natural_boot()


@app.delete("/api/neurons/nodes/{node_id}", dependencies=[Depends(_require_api_key)])
def api_delete_node(node_id: str):
    return neurons.delete_node(node_id)


@app.on_event("startup")
def on_startup():
    """Warm the graph and ensure vault exists."""
    import logging
    logging.basicConfig(level=logging.INFO)
    try:
        neurons.natural_boot()
    except Exception as e:
        logging.error("natural_boot failed: %s", e)
