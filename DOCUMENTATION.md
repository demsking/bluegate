**BlueGate** is ???.

Project repository: https://gitlab.com/demsking/bluegate

![BlueGate Logo](./static/logo.png)

## Core Capabilities

- Expose Zigbee2MQTT devices through the Model Context Protocol (MCP).
- Discover and inspect connected smart home devices.
- Read the current state and attributes of supported devices.
- Control lights, switches, plugs, locks, covers, and other actuators.
- Retrieve sensor measurements, including temperature, humidity, power,
  occupancy, and more.
- Execute device-specific actions through a unified interface.
- Automatically reflect changes reported by Zigbee2MQTT.
- Provide a consistent API regardless of the underlying Zigbee device.
- Support AI assistants and autonomous agents with structured MCP tools.
- Secure access to smart home devices using configurable authentication.
- Run as a lightweight Docker container with simple deployment.
- Integrate seamlessly with the Oremi ecosystem and other MCP-compatible
  clients.

## Deployment

BlueGate is distributed as a multi-platform Docker image for
`linux/amd64` and `linux/arm64`. It can be deployed as a standalone service or
integrated into the Oremi ecosystem alongside services such as Oremi Isinmi,
Oremi Ojọ, Oremi Rediyo, and Oremi Kansa.

The following sections describe the available Docker image, persistent storage
requirements, and example deployments using both Docker and Docker Compose.

### Command Line

Before installing BlueGate from PyPI, ensure the following requirements are
met:

- Python 3.12 or later.
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
Docker image is officially available on Docker Hub, supporting both
`linux/amd64` and `linux/arm64` platforms. The image exposes port `8765`, which
serves the REST API and the interactive documentation.

The interactive documentation can be accessed at `http://localhost:8765/docs/`
and allows testing available endpoints directly from the browser.

### Docker Volume

The Docker image defines a persistent volume at `/oremi/data`.

This directory is used as the default storage location for:

- **FastEmbed Model Cache**: Downloaded model weights for semantic vector search
  (`BLUEGATE_EMBEDDING_CACHE_DIR`). Mounting this volume prevents
  re-downloading model files when the container is recreated.
- **Application Logs**: Rotating log files if `BLUEGATE_LOG_FILE` is
  configured to write to a path inside `/oremi/data` (e.g.,
  `/oremi/data/bluegate.log`).

Mounting a volume or host directory to `/oremi/data` is recommended to maintain
cache persistence across container restarts.

### Deploy with Docker

Use the official Docker image
[`demsking/bluegate`](https://hub.docker.com/r/demsking/bluegate)
to run BlueGate:

```sh
docker run -d \
  --name bluegate \
  --env-file <path_to_env_file> \
  -p 8765:8765 \
  -v bluegate-data:/oremi/data \
  demsking/bluegate
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#environment-variables) file containing the desired
configuration.

### Deploy with Docker Compose

Create a `compose.yaml` file:

```yaml
services:
```

Start the services with:

```sh
docker compose up -d
```

Once started, open the interactive documentation at:

```txt
http://localhost:8765/docs/
```

## Configuration

All environment variables use the `BLUEGATE_` prefix and may be placed in
a `.env` file.

### Server

- `BLUEGATE_SERVER_HOST`: bind address; default `0.0.0.0`.
- `BLUEGATE_SERVER_PORT`: bind port; default `8765`.
- `BLUEGATE_API_PREFIX`: optional route prefix; default `/`.

### Logging

- `BLUEGATE_LOG_LEVEL`: Optional. Defaults to `INFO`. Logging level:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `BLUEGATE_LOG_FILE`: Optional. Defaults to unset (console logging only). Path to
  the rotating application log file.

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
