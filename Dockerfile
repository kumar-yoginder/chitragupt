# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-alpine AS builder

# Install build dependencies needed to compile C extensions (pydantic-core, etc.)
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /build/venv \
    && /build/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /build/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Final (minimal Alpine image) ───────────────────────────────────
FROM python:3.12-alpine

# Install only the bare-essential system dependencies
# su-exec: lightweight setuid for dropping root in the entrypoint
RUN apk add --no-cache perl exiftool su-exec

# Create a dedicated non-root user and group
RUN addgroup -S chitragupt_group \
    && adduser -S chitragupt_user -G chitragupt_group

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /build/venv /app/venv

# Copy application source code (read-only for the user later)
COPY . .

# Set root ownership for read-only app code, then grant the app user
# read+execute access to everything.
# data/ and logs/ permissions are fixed at runtime by entrypoint.sh
# because bind-mounted volumes override build-time ownership.
RUN chown -R root:chitragupt_group /app \
    && chmod -R a+rX /app \
    && chmod +x /app/entrypoint.sh

# Ensure the venv Python is on PATH
ENV PATH="/app/venv/bin:${PATH}"

# Entrypoint fixes dir permissions then drops to chitragupt_user
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "main.py"]
