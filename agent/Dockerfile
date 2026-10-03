FROM python:3.12-slim

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create a non-privileged system user and runtime directories
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -d /home/appuser -s /bin/bash appuser && \
    mkdir -p /app /data /home/appuser/.cache && \
    chown -R appuser:appgroup /app /data /home/appuser

WORKDIR /app

COPY --chown=appuser:appgroup pyproject.toml uv.lock README.md livekit.toml ./

USER appuser

RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appgroup src ./src

RUN uv sync --frozen --no-dev

# Pre-cache Silero VAD model during build for fast hermetic startup
RUN uv run python -c "from livekit.plugins import silero; silero.VAD.load()"

CMD ["uv", "run", "python", "-m", "voicedesk.main", "start"]
