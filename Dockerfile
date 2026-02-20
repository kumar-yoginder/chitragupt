# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

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

# Create data/ and logs/ directories owned by the app user with 755 permissions
RUN mkdir -p /app/data /app/logs \
    && chown chitragupt_user:chitragupt_group /app/data /app/logs \
    && chmod 755 /app/data /app/logs

# Make the rest of the application code read-only for the app user
RUN chown -R root:chitragupt_group /app \
    && chmod -R a+rX /app \
    && chown chitragupt_user:chitragupt_group /app/data /app/logs

# Ensure the venv Python is on PATH
ENV PATH="/app/venv/bin:${PATH}"

# Drop all kernel capabilities
USER chitragupt_user

CMD ["python", "main.py"]
