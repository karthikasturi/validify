# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder
# Install all dependencies and build the wheel into a prefix directory.
# Keeping build tools out of the runtime image reduces the attack surface
# and final image size.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
COPY src/ src/

# Install into /install so the runtime stage can COPY just that directory.
RUN pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir --prefix=/install .

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime
# Only the installed packages, application source, and config are copied.
# Build tools (pip, hatchling, git) are absent from this image.
# Running as a non-root user (appuser) limits the blast radius of any
# container escape or code-execution vulnerability.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

# Copy application source and declarative config.
COPY src/ src/
COPY config/ config/

# Create a non-root user and switch to it.
# Processes running as root inside a container are root on the host if the
# container runtime is misconfigured — non-root is a defence-in-depth measure.
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# PYTHONUNBUFFERED=1 ensures log output appears immediately in docker logs.
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "validify.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
