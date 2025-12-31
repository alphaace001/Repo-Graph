FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Node.js for npx (required for FastMCP inspector UI)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install MCP inspector globally to avoid runtime installation
RUN npm install -g @modelcontextprotocol/inspector@0.15.0

# Copy the entire KG-Assignment project
COPY . /app/

# Install Python dependencies from Analyst requirements
RUN pip install --no-cache-dir -r /app/MCP/Analyst/requirements.txt

# Set working directory to the Analyst MCP
WORKDIR /app/MCP/Analyst

# Environment variables to bind inspector to all interfaces (for Docker access)
ENV HOST=0.0.0.0
ENV CLIENT_PORT=6274
ENV SERVER_PORT=6277

# Expose MCP Inspector ports
EXPOSE 6274 6277

# Run the MCP server with inspector UI
CMD ["npx", "@modelcontextprotocol/inspector", "--", "python", "main.py"]
