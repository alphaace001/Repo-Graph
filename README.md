# Knowledge Graph Assignment

A FastAPI-based Knowledge Graph system with MCP (Model Context Protocol) services for code analysis, graph querying, and indexing.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Server (:8000)                     │
│                   FastAPI Backend + Agent                   │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
      ┌────────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
      │   Analyst     │ │Graph Query│ │   Indexer   │
      │   (:8001)     │ │  (:8002)  │ │   (:8003)   │
      └───────────────┘ └─────┬─────┘ └─────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Neo4j (:7687)   │
                    │   Browser (:7474) │
                    └───────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Neo4j (or use Docker)

### Clone the Repository

```bash
git clone <repository-url>
cd KG-Assignment
```

---

## Option 1: Docker Compose (Recommended)

Run all services with a single command:

```bash
# Start all services
docker-compose up --build

# Run in background
docker-compose up --build -d

# Stop all services
docker-compose down
```

### Service URLs (Docker)

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Neo4j Browser | http://localhost:7474 |
| Analyst MCP | http://localhost:8001/sse |
| Graph Query MCP | http://localhost:8002/sse |
| Indexer MCP | http://localhost:8003/sse |

### Environment Variables

Create a `.env` file or set these variables:

```bash
NEO4J_PASSWORD=your_password
```

---

## Option 2: Local Development

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Neo4j

Either run Neo4j locally or use Docker:

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15-community
```

### 3. Configure Environment

Create a `.env` file:

```bash
NEO4J_URL=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
API_HOST=0.0.0.0
API_PORT=8000
```

### 4. Run the API Server

```bash
python main.py
```

The API will start at http://localhost:8000

---

## Running Individual MCP Services

Each MCP service can be run standalone for development or testing.

### Analyst Service

```bash
cd MCP/Analyst
pip install -r requirements.txt
python main.py
```

### Graph Query Service

```bash
cd MCP/Graph_Query
pip install -r requirements.txt
python main.py
```

### Indexer Service

```bash
cd MCP/Indexer
pip install -r requirements.txt
python main.py
```

> **Note**: When running locally, MCP services use **stdio** transport. When running in Docker, they use **SSE** transport on their respective ports.

---

## MCP Tools Available

### Analyst (3 tools)
- `analyze_function` - Analyze function nodes in the knowledge graph
- `analyze_class` - Analyze class nodes and their relationships
- `get_code_snippet` - Extract code snippets with context

### Graph Query (7 tools)
- `find_entity` - Search for entities by name
- `get_dependencies` - Get outgoing dependencies
- `get_dependents` - Get incoming dependencies
- `trace_imports` - Follow import chains
- `find_related` - Find related entities by relationship type
- `execute_query` - Run custom Cypher queries (read-only)
- `get_code_statistics` - Get codebase statistics

### Indexer (4 tools)
- `extract_entities_tool` - Extract entities from Python files
- `ingest_all_files_tool` - Ingest entire codebase
- `process_single_file_tool` - Process a single file
- `parse_python_file_tool` - Parse Python AST

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check for all services |
| POST | `/api/chat` | Chat with the AI agent |

### Chat Example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Find all functions in the codebase"}'
```

---

## Project Structure

```
KG-Assignment/
├── API/                  # FastAPI backend
│   ├── main.py          # API server with chat endpoint
│   └── health.py        # Health check module
├── MCP/                  # MCP Services
│   ├── Analyst/         # Code analysis service
│   ├── Graph_Query/     # Graph querying service
│   └── Indexer/         # Code indexing service
├── Client/              # LLM client and agent
├── Database/            # Neo4j connection
├── main.py              # Entry point
├── config.py            # Configuration
├── docker-compose.yml   # Docker orchestration
├── Dockerfile           # API container
└── requirements.txt     # Python dependencies
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process using the port
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Neo4j Connection Failed
- Ensure Neo4j is running: `docker ps`
- Check credentials in `.env`
- Verify URL format: `neo4j://localhost:7687`

### Docker Build Issues
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

---

## License

MIT License