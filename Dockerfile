# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for CampusVoice (React + Flask single container deployment on Railway)

# ==========================================
# Stage 1: Build React Production Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy npm package definitions and lockfile
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source files
COPY frontend/ ./

# Compile production bundle to /app/frontend/dist
RUN npm run build


# ==========================================
# Stage 2: Python Runtime & Waitress Server
# ==========================================
FROM python:3.11-slim AS runner

# Optimize Python execution in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000 \
    HOST=0.0.0.0 \
    FLASK_ENV=production \
    UPLOAD_FOLDER=/data/uploads \
    SQLITE_PATH=/data/campusvoice.db

WORKDIR /app

# Install curl for container healthcheck and basic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first to prevent downloading heavy CUDA/GPU wheels (~2GB saved)
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

# Copy and install python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy backend application source
COPY app/ ./app/
COPY run.py ./run.py

# Copy pre-compiled React distribution from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create base data directory (overlaid at runtime when Railway Volume is mounted to /data)
RUN mkdir -p /data/uploads

# Expose port (Railway dynamically injects $PORT at runtime)
EXPOSE 5000

# Docker Healthcheck targeting the dedicated health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-5000}/api/health || exit 1

# Start Waitress production server (binds to 0.0.0.0 and runtime $PORT in run.py)
CMD ["python", "run.py"]

