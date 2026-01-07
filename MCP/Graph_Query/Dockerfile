FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire KG-Assignment project
COPY . /app/

# Install Python dependencies from Graph_Query requirements
RUN pip install --no-cache-dir -r /app/MCP/Graph_Query/requirements.txt

# Set working directory to the Graph_Query MCP
WORKDIR /app/MCP/Graph_Query

# Environment variables for Docker mode
ENV DOCKER_MODE=true
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8002
ENV PYTHONPATH=/app

# Expose SSE port
EXPOSE 8002

# Run the MCP server in SSE mode
CMD ["python", "main.py"]
