# Use Python 3.12 slim image to match your local environment
FROM python:3.12-slim-bookworm

# Install system dependencies for scipy, numpy, pandas, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set Docker environment flag for automatic detection in SecretsLoader
ENV DOCKER_CONTAINER=true

# IMPORTANT: Credentials should be injected at runtime via:
# - Environment variables
# - Docker secrets
# - Kubernetes secrets
# - Cloud platform secret management services
# DO NOT hardcode credentials in Docker image

# Set the default command to run your Flask web API
CMD ["python", "-m", "src.stockreports.web"]
