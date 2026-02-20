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
RUN apk add --no-cache perl exiftool

# Create a dedicated non-root user and group
RUN addgroup -S chitragupt_group \
    && adduser -S chitragupt_user -G chitragupt_group

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /build/venv /app/venv

# Copy application source code (read-only for the user later)
COPY . .

# Set root ownership for read-only app code, then grant the app user
# write access only to data/ and logs/ (755)
RUN mkdir -p /app/data /app/logs \
    && chown -R root:chitragupt_group /app \
    && chmod -R a+rX /app \
    && chown chitragupt_user:chitragupt_group /app/data /app/logs \
    && chmod 755 /app/data /app/logs

# Ensure the venv Python is on PATH
ENV PATH="/app/venv/bin:${PATH}"

# Drop all kernel capabilities
USER chitragupt_user

CMD ["python", "main.py"]
