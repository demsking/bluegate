# BlueGate UI

BlueGate UI is a standalone web dashboard that can manage Bluetooth gateways from multiple BlueGate nodes.

## Local development

1. Install dependencies:

```bash
npm install
```

2. Start the dev server:

```bash
npm run dev
```

## Runtime configuration

The container configures nodes at startup through environment variables:

- `BLUEGATE_NODES_JSON`: JSON array with node metadata and upstream mapping.

Each node ID is now resolved through an internal same-origin proxy path.
For a node with `id: "bamenda"`, the UI calls:

- REST: `${window.location.origin}/bamenda/api/...`
- WebSocket: `${window.location.origin}/bamenda/api/ws/`

The proxy is expected to route `/bamenda/*` to the target BlueGate server
(for example, `http://192.168.1.60:18765`).

```json
[
  { "id": "node-a", "name": "Node A", "server": "http://bluegate-node-a:8765" },
  { "id": "node-b", "name": "Node B", "server": "http://bluegate-node-b:8765" }
]
```

At container startup, the entrypoint parses `BLUEGATE_NODES_JSON` to:

- Generate nginx proxy locations (`/{id}/...` -> `server` upstream).
- Generate `/nodes.json` containing only public node metadata:

```json
[
  { "id": "node-a", "name": "Node A" },
  { "id": "node-b", "name": "Node B" }
]
```

## Docker

Build and run directly:

```bash
docker build -t bluegate-ui .
docker run --rm -p 8080:8080 \
  -e 'BLUEGATE_NODES_JSON=[{"id":"local","name":"Local node","server":"http://host.docker.internal:8765"}]' \
	bluegate-ui
```

For local Vite development, add `BLUEGATE_NODES_JSON` to `.env` (or `.env.local`).
The Vite dev server uses node `server` values to proxy `/{id}/...` requests.

Or use Compose inside [ui/compose.yaml](compose.yaml):

```bash
docker compose up --build
```
