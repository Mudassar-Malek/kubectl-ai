# K8s IntelliBot - Production Dockerfile
# Multi-stage build for minimal image size

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim as runtime

WORKDIR /app

# Install kubectl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash k8sbot
USER k8sbot

# Copy application code
COPY --chown=k8sbot:k8sbot src/ ./src/
COPY --chown=k8sbot:k8sbot pyproject.toml ./

# Create directory for kubeconfig mounting
RUN mkdir -p /home/k8sbot/.kube

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KUBECONFIG=/home/k8sbot/.kube/config

# Default command
ENTRYPOINT ["python", "-m", "src.main"]
CMD []

# Labels
LABEL org.opencontainers.image.title="K8s IntelliBot" \
    org.opencontainers.image.description="AI-powered Kubernetes assistant" \
    org.opencontainers.image.vendor="K8s IntelliBot Team" \
    org.opencontainers.image.source="https://github.com/your-org/k8s-intellibot"
