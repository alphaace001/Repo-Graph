FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire KG-Assignment project
COPY . /app/

# Install Python dependencies from Indexer requirements
RUN pip install --no-cache-dir -r /app/MCP/Indexer/requirements.txt

# Set working directory to the Indexer MCP
WORKDIR /app/MCP/Indexer

# Environment variables for Docker mode
ENV DOCKER_MODE=true
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8003

# Expose SSE port
EXPOSE 8003

# Run the MCP server in SSE mode
CMD ["python", "main.py"]
