#
## Stage 1: Builder
FROM python:3.12-alpine AS builder

ENV UV_LINK_MODE=copy

# Set the shell
SHELL ["/bin/sh", "-c"]

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  set -eux; \
  uv sync --no-dev --locked --no-install-project --compile-bytecode \
      && find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
      && find /app/.venv -type d \( -name "tests" -o -name "test" -o -name "testing" \) -exec rm -rf {} + 2>/dev/null || true \
      && find /app/.venv -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.exe" \) -delete 2>/dev/null || true

#
## Stage 2: Final
FROM python:3.12-alpine

# Set the shell
SHELL ["/bin/sh", "-c"]

RUN addgroup -S bluegate && adduser -S -D -G bluegate -h /demsking bluegate

WORKDIR /demsking

COPY --from=builder /app/.venv /demsking/.venv

COPY --chown=bluegate:bluegate pyproject.toml LICENSE DOCUMENTATION.md ./
COPY --chown=bluegate:bluegate htdocs/ ./htdocs/
COPY --chown=bluegate:bluegate bluegate/ ./bluegate/

ENV PATH="/demsking/.venv/bin:$PATH"
ENV PYTHONPATH="/demsking:/demsking/.venv/lib/python3.12/site-packages"
ENV PYTHONUNBUFFERED="1"

ENV BLUEGATE_LOG_LEVEL="INFO"
ENV BLUEGATE_SERVER_HOST="0.0.0.0"
ENV BLUEGATE_SERVER_PORT="8765"

EXPOSE 8765

# HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
#   CMD python -c "import urllib.request; prefix='${BLUEGATE_API_PREFIX}'.strip('/'); url=f'http://localhost:${BLUEGATE_SERVER_PORT}/' + (prefix + '/' if prefix else '') + 'health/'; urllib.request.urlopen(url)" || exit 1

CMD ["python", "/demsking/bluegate"]
