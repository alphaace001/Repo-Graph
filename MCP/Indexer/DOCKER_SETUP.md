# Indexer MCP Server Docker Setup

## Building the Docker Image

> **Important**: The Dockerfile must be built from the `KG-Assignment` root directory (not the Indexer folder) because it copies the entire project.

```bash
# Navigate to KG-Assignment root directory
cd d:\KGassign\KG-Assignment

# Build the image (specify Dockerfile path with -f)
docker build -t indexer-mcp:latest -f MCP/Indexer/Dockerfile .
```

## Running the Container

### Option 1: Using Docker Compose (Recommended)

```bash
cd d:\KGassign\KG-Assignment\MCP\Indexer
docker-compose up -d
```

### Option 2: Using Docker Directly

```bash
docker run -it \
  --name indexer-mcp-server \
  -e BASE_PATH=/data/fastapi \
  -v "D:\KGassign\fastapi":/data/fastapi:ro \
  -v "D:\KGassign\KG-Assignment":/app \
  indexer-mcp:latest
```

## Understanding MCP stdio Transport

This server uses **stdio transport** (not HTTP). It reads JSON-RPC messages from stdin and writes responses to stdout.

### Testing Manually

After running the container, you must initialize the MCP handshake:

**Step 1: Initialize connection**
```json
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}
```

**Step 2: Send initialized notification**
```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

**Step 3: List available tools**
```json
{"jsonrpc":"2.0","method":"tools/list","id":2}
```

### Using with Claude Desktop (Recommended)

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "indexer": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "D:\\KGassign\\fastapi:/data/fastapi:ro",
        "-v", "D:\\KGassign\\KG-Assignment:/app",
        "indexer-mcp:latest"
      ]
    }
  }
}
```

## Environment Variables

- `BASE_PATH`: Path to the FastAPI codebase (default: `/data/fastapi`)
- `PYTHONUNBUFFERED`: Set to 1 for real-time output logging

## Volumes

- `/data/fastapi`: Mount point for the FastAPI codebase (read-only)
- `/app`: Mount point for the KG-Assignment directory (for database access)

## Logs

```bash
docker logs -f indexer-mcp-server
```

## Stopping the Container

```bash
docker-compose down
# or
docker stop indexer-mcp-server
# or press Ctrl+C if running interactively
```

## Rebuilding the Image

```bash
docker-compose down
docker rmi indexer-mcp:latest
cd d:\KGassign\KG-Assignment
docker build -t indexer-mcp:latest -f MCP/Indexer/Dockerfile .
docker-compose -f MCP/Indexer/docker-compose.yml up -d
```
