# Use Python 3.9 slim image to match your local environment
FROM python:3.9-slim-bullseye

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

# Set the default command to run your Flask web API
CMD ["python", "src/stockreports/web.py"]
