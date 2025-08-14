# Multi-stage build for smaller final image
FROM python:3.11-slim AS base

# Set production environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/home/nuclei/.local/bin:$PATH"

# Create non-root user for security
RUN groupadd -r nuclei && useradd -r -g nuclei nuclei

# Set working directory
WORKDIR /app

# Install only runtime system dependencies (without specifying versions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    ca-certificates \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies in builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt \
    && find /root/.local -name "*.pyc" -delete \
    && find /root/.local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /root/.local -name "*.dist-info" -type d -exec rm -rf {}/RECORD {} + 2>/dev/null || true

# Final runtime stage
FROM base

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/nuclei/.local

# Create necessary directories with proper permissions
RUN mkdir -p logs rag_data config templates \
    && chown -R nuclei:nuclei /app /home/nuclei/.local

# Copy application code (do this after creating directories for better caching)
COPY --chown=nuclei:nuclei . .

# Switch to non-root user
USER nuclei

# Expose port
EXPOSE 8000

# Improved health check with better configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${API_PORT:-8000}/health -A "HealthCheck/1.0" --max-time 8 || exit 1

# Use dumb-init for better signal handling and process management
CMD ["dumb-init", "python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--http", "httptools"]