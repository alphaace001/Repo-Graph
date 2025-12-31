"""
Configuration Module - Centralized configuration for MCP servers and services
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_PATH = Path(__file__).parent
VENV_PATH = BASE_PATH / ".venv" / "Scripts" / "python.exe"
MCP_PATH = BASE_PATH / "MCP"

# Environment variables for MCP servers
server_env = os.environ.copy()
server_env["FASTMCP_QUIET"] = "1"

# MCP Server configurations
MCP_SERVERS = {
    "analyst": {
        "transport": "stdio",
        "command": str(VENV_PATH),
        "args": [str(MCP_PATH / "Analyst" / "main.py")],
        "env": server_env,
    },
    "graph-query": {
        "transport": "stdio",
        "command": str(VENV_PATH),
        "args": [str(MCP_PATH / "Graph_Query" / "main.py")],
        "env": server_env,
    },
    "indexer": {
        "transport": "stdio",
        "command": str(VENV_PATH),
        "args": [str(MCP_PATH / "Indexer" / "main.py")],
        "env": server_env,
    },
}

# Service display names
SERVICE_NAMES = {
    "analyst": "Analyst Service",
    "graph-query": "Graph Query Service",
    "indexer": "Indexer Service",
}

# Neo4j configuration
NEO4J_URL = os.getenv("NEO4J_URL", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# API configuration
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Health check configuration
HEALTH_CHECK_TIMEOUT = 10  # seconds

# Agent configuration
AGENT_RECURSION_LIMIT = 150
