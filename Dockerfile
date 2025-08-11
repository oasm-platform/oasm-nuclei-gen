# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies in builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r nuclei && useradd -r -g nuclei nuclei

# Set working directory
WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/nuclei/.local

# Install Nuclei binary with version validation
ARG NUCLEI_VERSION=2.9.15
RUN wget -q "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && echo "Downloading Nuclei ${NUCLEI_VERSION}..." \
    && unzip "nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && mv nuclei /usr/local/bin/ \
    && chmod +x /usr/local/bin/nuclei \
    && rm "nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
    && nuclei -version

# Create necessary directories with proper permissions
RUN mkdir -p logs rag_data config templates \
    && chown -R nuclei:nuclei /app

# Copy application code
COPY --chown=nuclei:nuclei . .

# Ensure Python path includes user packages
ENV PATH="/home/nuclei/.local/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER nuclei

# Expose port
EXPOSE 8000

# Improved health check that matches docker-compose configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:${API_PORT:-8000}/api/v1/health || exit 1

# Use exec form for better signal handling
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]