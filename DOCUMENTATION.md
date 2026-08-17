**BlueGate** is a Bluetooth gateway and device manager focused on exposing
Bluetooth operations to external systems through a lightweight HTTP service.

Project repository: https://gitlab.com/demsking/bluegate

![BlueGate Logo](./static/logo.png)

## Core Capabilities

- Bluetooth adapter discovery and status reporting.
- Device discovery and inventory for nearby peripherals.
- Pairing lifecycle operations (pair, trust, remove).
- GATT browsing and interaction primitives for services,
  characteristics, and descriptors.
- WebSocket event streaming for real-time Bluetooth state updates.
- Configurable runtime behavior through environment variables.

## Deployment

BlueGate is distributed as a multi-platform Docker image for
`linux/amd64` and `linux/arm64` and can be deployed as a standalone service.

The following sections describe the available Docker image, persistent storage
requirements, and example deployments using both Docker and Docker Compose.

### Command Line

Before installing BlueGate from PyPI, ensure the following requirements are met:

- Python 3.11 or later.
- `uv` (recommended) or `pip` for package installation.

BlueGate can be installed either as a standalone command-line application
or as a Python package.

#### Install with uv

```sh
uv tool install bluegate
```

#### Install with pip

```sh
pip install bluegate
```

#### Usage

```text
bluegate [-h] [-v]
```

When started without arguments, BlueGate launches the HTTP server using the
configured environment variables.

#### Options

- `-h`, `--help`: Display the command-line help and exit.
- `-v`, `--version`: Display the installed version and exit.

### Docker Image

The [`demsking/bluegate`](https://hub.docker.com/r/demsking/bluegate)
Docker image is officially available on Docker Hub and supports both
`linux/amd64` and `linux/arm64` platforms.

The container exposes port `8765` for the BlueGate service.

### Deploy with Docker

Use the official Docker image
[`demsking/bluegate`](https://hub.docker.com/r/demsking/bluegate)
to run BlueGate:

```sh
docker run -d \
  --name bluegate \
  --env-file <path_to_env_file> \
  -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro \
  -e BLUEGATE_DBUS_SYSTEM_BUS=unix:path=/run/dbus/system_bus_socket \
  -p 8765:8765 \
  demsking/bluegate
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#configuration) file containing the desired
configuration.

### Deploy with Docker Compose

Create a `compose.yaml` file:

```yaml
services:
  bluegate:
    image: demsking/bluegate:latest
    container_name: bluegate
    restart: unless-stopped
    env_file:
      - .env
    environment:
      BLUEGATE_DBUS_SYSTEM_BUS: unix:path=/run/dbus/system_bus_socket
    volumes:
      - /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro
    ports:
      - "8765:8765"
```

Start the services with:

```sh
docker compose up -d
```

BlueGate will be available on `http://localhost:8765`.

To enable Bluetooth features from a container, ensure the host is running
both `dbus` and `bluetoothd`, and that the system bus socket is mounted into
the container as shown above.

## Configuration

All environment variables use the `BLUEGATE_` prefix and may be placed in
a `.env` file.

### Server

- `BLUEGATE_SERVER_HOST`: Bind address. Default: `127.0.0.1`.
- `BLUEGATE_SERVER_PORT`: bind port; default `8765`.
- `BLUEGATE_API_PREFIX`: optional route prefix; default `/`.

### Bluetooth

- `BLUEGATE_DBUS_SYSTEM_BUS`: Optional D-Bus system bus address.
- `BLUEGATE_BLUETOOTH_AGENT_CAPABILITY`: Agent capability. One of:
  `DisplayOnly`, `DisplayYesNo`, `KeyboardOnly`, `NoInputNoOutput`,
  `KeyboardDisplay`. Default: `DisplayYesNo`.
- `BLUEGATE_SCAN_TIMEOUT`: Default scan timeout in seconds. Default: `20`.

### Real-Time

- `BLUEGATE_WEBSOCKET_HEARTBEAT`: WebSocket heartbeat interval in seconds.
  Default: `30`.
- `BLUEGATE_CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins.
  Default: disabled (empty). Browser cross-origin requests are blocked unless
  this setting is explicitly configured.

### UI Proxy Pattern

BlueGate UI now targets BlueGate servers through an internal same-origin proxy.
The UI node definition includes `id`, `name`, and `server`. For a node with
`id=bamenda`, UI requests are emitted as:

- `https://<ui-host>/bamenda/api/adapters/`
- `wss://<ui-host>/bamenda/api/ws/`

Your reverse proxy should route `/bamenda/*` to the corresponding BlueGate
server (for example `http://192.168.1.60:18765`).

When using the bundled BlueGate UI container, configure routing with
`BLUEGATE_NODES_JSON`, for example:

```json
[
  {
    "id": "bamenda",
    "name": "Bamenda node",
    "server": "http://192.168.1.60:18765"
  },
  {
    "id": "yaounde",
    "name": "Yaounde node",
    "server": "http://192.168.1.61:18765"
  }
]
```

At startup, the UI entrypoint generates `/nodes.json` from this config with
only public metadata (`id`, `name`), and the frontend loads that file.

### Logging

- `BLUEGATE_LOG_LEVEL`: Optional. Defaults to `INFO`. Logging level:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `BLUEGATE_LOG_FILE`: Optional. Defaults to unset (console logging only).
  Path to the rotating application log file.

## Development

See the [contribution guide](https://gitlab.com/demsking/bluegate/-/blob/main/CONTRIBUTING.md)
for development environment and contribution guidance.

## Versioning

BlueGate project adheres to [Semantic Versioning](https://semver.org/)
(SemVer). Version numbers follow the `MAJOR.MINOR.PATCH` format:

- **MAJOR** version increments for incompatible API changes
- **MINOR** version increments for backward-compatible new functionality
- **PATCH** version increments for backward-compatible bug fixes

The current version can be found by running:

```bash
bluegate --version
```

## License

Copyright 2026 Sébastien Demanou. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://gitlab.com/demsking/bluegate/-/blob/main/LICENSE

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
