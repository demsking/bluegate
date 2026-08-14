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

- `UI_NODES_JSON`: JSON array of nodes:

```json
[
  { "id": "node-a", "name": "Node A", "apiBaseUrl": "http://node-a:8765" },
  { "id": "node-b", "name": "Node B", "apiBaseUrl": "http://node-b:8765" }
]
```

- `UI_DEFAULT_NODE_ID`: default selected node id.

## Docker

Build and run directly:

```bash
docker build -t bluegate-ui .
docker run --rm -p 8080:8080 \
	-e 'UI_NODES_JSON=[{"id":"local","name":"Local node","apiBaseUrl":"http://127.0.0.1:8765"}]' \
	-e UI_DEFAULT_NODE_ID=local \
	bluegate-ui
```

Or use Compose inside [ui/compose.yaml](compose.yaml):

```bash
docker compose up --build
```
