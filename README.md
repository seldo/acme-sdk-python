# Acme SDK for Python

[![CI](https://github.com/acme-corp/acme-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/acme-corp/acme-sdk-python/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/acme-sdk.svg)](https://badge.fury.io/py/acme-sdk)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

The official Python SDK for the [Acme Observability Platform](https://acme-sdk.dev). Collect, export, and analyze traces, spans, and metrics from your applications with minimal configuration.

## Features

- **Distributed Tracing** — Capture traces and spans with full context propagation
- **Multiple Exporters** — Ship data via OTLP, JSON files, or console output
- **Flexible Authentication** — API key and OAuth 2.0 support
- **Batch Processing** — Efficiently batch and compress telemetry data
- **Automatic Retries** — Configurable retry logic with exponential backoff
- **Configuration Management** — YAML/TOML config files with environment variable interpolation

## Installation

```bash
pip install acme-sdk
```

For gRPC transport support:

```bash
pip install acme-sdk[grpc]
```

## Quick Start

```python
from acme_sdk import AcmeClient
from acme_sdk.models import Span, Event
from acme_sdk.exporters.otlp import OTLPExporter

# Initialize the client
client = AcmeClient(
    api_key="your-api-key",
    endpoint="https://ingest.acme-sdk.dev",
)

# Create and export a span
span = Span(
    name="process_request",
    service_name="my-service",
    duration_ms=142.5,
    attributes={"http.method": "GET", "http.status_code": 200},
)

# Export using OTLP
exporter = OTLPExporter(client=client)
exporter.export([span])
```

## Configuration

You can configure the SDK via code, environment variables, or a config file:

```python
from acme_sdk.config import AcmeConfig

# From environment variables
config = AcmeConfig.from_env()

# From a config file
config = AcmeConfig.from_file("acme.toml")
```

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ACME_API_KEY` | API key for authentication | — |
| `ACME_ENDPOINT` | Ingest endpoint URL | `https://ingest.acme-sdk.dev` |
| `ACME_TIMEOUT` | Request timeout in seconds | `30` |
| `ACME_COMPRESSION` | Enable gzip compression | `true` |
| `ACME_BATCH_SIZE` | Max spans per batch | `512` |

## Exporters

The SDK ships with three built-in exporters:

### OTLP Exporter

The recommended exporter for production use. Sends data via HTTP using the OpenTelemetry Protocol.

```python
from acme_sdk.exporters.otlp import OTLPExporter

exporter = OTLPExporter(client=client, compression=True)
exporter.export(spans)
```

### JSON File Exporter

Writes telemetry data to local JSON files. Useful for debugging and local development.

```python
from acme_sdk.exporters.json_file import JSONFileExporter

exporter = JSONFileExporter(output_dir="./traces")
exporter.export(spans)
```

### Console Exporter

Prints telemetry data to stdout. Great for development and debugging.

```python
from acme_sdk.exporters.console import ConsoleExporter

exporter = ConsoleExporter(colorize=True)
exporter.export(spans)
```

## Authentication

The SDK supports two authentication methods:

### API Key

```python
client = AcmeClient(api_key="your-api-key")
```

### OAuth 2.0

```python
from acme_sdk.auth import OAuthProvider

auth = OAuthProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.acme-sdk.dev/oauth/token",
)
client = AcmeClient(auth_provider=auth)
```

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Exporters Guide](docs/exporters.md)
- [API Reference](docs/api-reference.md)

## Development

```bash
# Clone the repo
git clone https://github.com/acme-corp/acme-sdk-python.git
cd acme-sdk-python

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Type checking
mypy src/
```

## Contributing

We welcome contributions! Please see our contributing guidelines and make sure to:

1. Fork the repository
2. Create a feature branch
3. Add tests for any new functionality
4. Ensure all tests pass and linting is clean
5. Open a pull request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/acme-corp/acme-sdk-python/issues)
- **Docs**: [docs.acme-sdk.dev](https://docs.acme-sdk.dev)
- **Email**: sdk-support@acme-sdk.dev

When you receive an error, please check the [troubleshooting guide](docs/configuration.md#troubleshooting) before opening an issue.
