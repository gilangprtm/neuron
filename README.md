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

The all-in-one pattern — single docker-compose.yml on VPS:
```yaml
version: '3.8'

services:
  neuron:
    build: .
    container_name: neuron
    volumes:
      - neuron-data:/app/data
      - neuron-vault:/app/Neuron-Vault
    ports:
      - "9120:9120"
    environment:
      - NEURON_API_KEY=change-me
      - NEURON_VAULT_PATH=/app/Neuron-Vault
    restart: unless-stopped

  hermes:
    image: hermes:latest
    container_name: hermes
    depends_on:
      - neuron
    volumes:
      - hermes-data:/app/data
      - neuron-vault:/app/Neuron-Vault   # same volume
    ports:
      - "9119:9119"
    environment:
      - NEURON_API_KEY=change-me
      - NEURON_HOST=http://neuron:9120
    restart: unless-stopped

volumes:
  neuron-data:
  neuron-vault:
  hermes-data:
```

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
uvicorn main:app --host 0.0.0.0 --port 9120
```

Health check:
```bash
curl http://localhost:9120/health
```

## Docker / Coolify

```bash
docker build -t neuron .
docker run -d \
  -p 9120:9120 \
  -e NEURON_API_KEY=change-me \
  -e NEURON_VAULT_PATH=/app/Neuron-Vault \
  -v neuron-data:/app/data \
  -v neuron-vault:/app/Neuron-Vault \
  neuron
```

Coolify: set build pack Docker, port 9120, env `NEURON_API_KEY` + `NEURON_VAULT_PATH`, volumes `/app/data` and `/app/Neuron-Vault`. Neuron-Vault is the shared volume Hermes will also mount.

## Deployment notes: Linux VPS vs Windows Docker Desktop

### Linux VPS (e.g. Coolify, Docker-Compose)
```
volumes:
  - host-path:/app/Neuron-Vault   # bind mount from host
```
Example: `- /home/sira/vault:/app/Neuron-Vault`

### Windows Docker Desktop
Windows absolute paths in Docker maps work as:
```
volumes:
  - C:/Users/gilang/Documents/Sao-Vault:/app/Neuron-Vault
```
Docker Desktop handles the translation automatically — inside the container `/app/Neuron-Vault` behaves identically to Linux. Hermes container mounts the same volume.

### Docker volumes (no bind)
If you prefer Docker-managed volumes (portable, no host path dependency):
```yaml
volumes:
  neuron-vault:

services:
  neuron:
    volumes:
      - neuron-vault:/app/Neuron-Vault
  hermes:
    volumes:
      - neuron-vault:/app/Neuron-Vault
```
This works identically on Linux and Windows — Docker Desktop maps it to a Windows path transparently.

### First boot
On first startup, Neuron Service auto-creates `Neuron-Vault/` with:
```
AGENTS.md  AGENTS-core.md  AGENTS-memory.md  SCHEMA.md
wiki/  raw/  Sessions/  Philosophy/  graphify-out/  _templates/
```
No manual creation needed. After creation, sync vault → graph runs automatically.

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
curl -X POST http://localhost:9120/api/neurons/remember \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"content":"CSP nonce must be generated BEFORE call_next","source":"hermes"}'

# Query
curl -X POST http://localhost:9120/api/neurons/activate \
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
