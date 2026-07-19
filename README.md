# Neuron Service

Standalone neural memory hub. Graph + FastEmbed + decay.
Any agent (Hermes, Odys, custom) can use it as a persistent brain.

## Features

- **Nodes**: memory, vault_note, project, session
- **Edges**: co-activation with weight / count / last_seen
- **Activate**: query → embed (FastEmbed 384-dim) → top-K nodes + spread
- **Strengthen**: Hebbian pairwise edge boost
- **Decay**: edges *= 0.9; drop weak; archive stale isolated nodes
- **Remember**: free-form fact import from any agent
- **Sync vault**: scan Obsidian markdown → vault_note nodes + wikilink edges

## Quick start (local)

```bash
cd D:/Project/neuron
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
export NEURON_API_KEY=change-me   # optional; empty = no auth
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check:
```bash
curl http://localhost:8000/health
```

## Docker / Coolify

```bash
docker build -t neuron .
docker run -d \
  -p 8000:8000 \
  -e NEURON_API_KEY=change-me \
  -e NEURON_VAULT_PATH=/app/vault \
  -v neuron-data:/app/data \
  -v /path/to/vault:/app/vault:ro \
  neuron
```

Coolify: set build pack Docker, port 8000, env `NEURON_API_KEY`, volume `/app/data`.

## API

All endpoints (except `/health`) require header `X-API-Key: <NEURON_API_KEY>`
when the env is set.

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness |
| GET | `/api/neurons/status` | — | Graph stats |
| GET | `/api/neurons/nodes` | `?include_archived=` | List nodes |
| POST | `/api/neurons/nodes` | `{type,label,ref,text?}` | Upsert node |
| POST | `/api/neurons/activate` | `{query, top_k?}` | Query graph |
| POST | `/api/neurons/strengthen` | `{ids:[...]}` | Boost edges |
| POST | `/api/neurons/decay` | — | Run decay pass |
| POST | `/api/neurons/remember` | `{content, source?, pinned?}` | Import fact |
| POST | `/api/neurons/sync-vault` | `{path?, link_wikilinks?}` | Scan vault |
| DELETE | `/api/neurons/nodes/{id}` | — | Delete node |

### Example: remember + activate

```bash
# Store a fact
curl -X POST http://localhost:8000/api/neurons/remember \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"content":"CSP nonce must be generated BEFORE call_next","source":"hermes"}'

# Query
curl -X POST http://localhost:8000/api/neurons/activate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"query":"CSP nonce middleware","top_k":5}'
```

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `NEURON_API_KEY` | empty | If set, require `X-API-Key` header |
| `NEURON_VAULT_PATH` | empty | Default vault for `/sync-vault` |

## Data

- `data/graph.db` — SQLite (WAL)
- `data/graph.json` — legacy / fallback
- `data/fastembed_cache/` — BAAI/bge-small-en-v1.5 model cache

## Hermes integration

Skill `neuron-client` (to be added) will:
1. Pre-turn: `POST /activate` → inject context
2. Post-turn / cron: `POST /remember` → store facts

## License

Private — Enki / Sira stack.
