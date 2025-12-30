# Indexer MCP Server Docker Setup

## Building the Docker Image

```bash
cd d:\KGassign\KG-Assignment\MCP\Indexer
docker build -t indexer-mcp:latest .
```

## Running the Container

### Option 1: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Option 2: Using Docker Directly

```bash
docker run -it \
  --name indexer-mcp-server \
  -e BASE_PATH=/data/fastapi \
  -v "D:\KGassign\fastapi":/data/fastapi:ro \
  -v "D:\KGassign\KG-Assignment":/app \
  -p 8000:8000 \
  indexer-mcp:latest
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
```

## Rebuilding the Image

```bash
docker-compose down
docker rmi indexer-mcp:latest
docker build -t indexer-mcp:latest .
docker-compose up -d
```
