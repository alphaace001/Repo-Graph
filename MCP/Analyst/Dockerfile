FROM python:3.11-slim

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

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Analyst application (all files from current directory)
COPY . .

# Expose port if needed (optional, MCP uses stdio)
# EXPOSE 8000

# Run the MCP server with inspector UI
CMD ["fastmcp", "dev", "main.py"]
