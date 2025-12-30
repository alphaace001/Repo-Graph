# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BASE_PATH=/data/fastapi

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire KG-Assignment project
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/MCP/Indexer/requirements.txt

# Change to the Indexer directory
WORKDIR /app/MCP/Indexer

# Expose the default MCP server port (if using stdio, this may not be needed)
EXPOSE 8000

# Set the entrypoint to run the MCP server
ENTRYPOINT ["python", "main.py"]
