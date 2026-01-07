FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire KG-Assignment project
COPY . /app/

# Install Python dependencies from Analyst requirements
RUN pip install --no-cache-dir -r /app/MCP/Analyst/requirements.txt

# Set working directory to the Analyst MCP
WORKDIR /app/MCP/Analyst

# Environment variables for Docker mode
ENV DOCKER_MODE=true
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001
ENV PYTHONPATH=/app

# Expose SSE port
EXPOSE 8001

# Run the MCP server in SSE mode
CMD ["python", "main.py"]
