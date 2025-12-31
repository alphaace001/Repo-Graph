"""
Indexer MCP Server - FastMCP implementation for code indexing.
Provides tools for extracting entities, ingesting files, and parsing Python AST.
"""

import ast
import sys
import os
from pathlib import Path

# Setup Python paths before importing anything else
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add KG-Assignment to path
sys.path.insert(0, str(Path(__file__).parent))  # Add Indexer to path
sys.path.insert(0, str(Path(__file__).parent / "Tools"))  # Add Tools to path
sys.path.insert(0, str(Path(__file__).parent / "Utils"))  # Add Utils to path

import json
from fastmcp import FastMCP
from dotenv import load_dotenv
from logger import get_mcp_safe_logger, mcp_tool_logged, configure_mcp_logging
from Tools.extract_entities import extract_entities
from Tools.index_repo import ingest_all_files
from Tools.process_single_file import ingest_single_file
from Tools.get_python_ast import parse_python_file

# Configure MCP-safe logging
configure_mcp_logging()
logger = get_mcp_safe_logger(__name__)

# Initialize the MCP server with increased timeout
mcp = FastMCP("indexer")

load_dotenv()
BASE_PATH = os.getenv("BASE_PATH", "D:\\KGassign\\fastapi")

logger.info(f"Indexer MCP server initialized with BASE_PATH={BASE_PATH}")


# Define the tools
@mcp.tool()
@mcp_tool_logged
def extract_entities_tool(file_path: str) -> str:
    """
    Extract entities (functions and classes) from a Python file.

    Args:
        file_path: Path to the Python file
        base_path: Base path for the codebase

    Returns:
        JSON string containing extracted entities
    """
    try:
        # Strip leading slashes/backslashes to avoid path issues
        file_path_clean = file_path.lstrip("/\\")
        full_path = str(Path(BASE_PATH) / file_path_clean)
        # Read and parse the file to get AST
        with open(full_path, "r", encoding="utf-8") as f:
            code_content = f.read()
        ast_code = ast.parse(code_content)

        # Call extract_entities with the AST
        result = extract_entities(ast_code, None, file_path)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
@mcp_tool_logged
def ingest_all_files_tool(path: str = "") -> str:
    """
    Ingest all Python files from a codebase into the knowledge graph.

    Args:
        path: Subdirectory path within the base path (optional, defaults to root)

    Returns:
        Status message about the ingestion process
    """
    try:
        # Strip leading slashes/backslashes to avoid path duplication
        path_clean = path.lstrip("/\\")
        # Construct full path: BASE_PATH + path
        if path_clean:
            full_path = str(Path(BASE_PATH) / path_clean)
        else:
            full_path = BASE_PATH
        ingest_all_files(full_path)
        return json.dumps(
            {
                "status": "success",
                "message": f"All files from {full_path} ingested successfully",
            }
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
@mcp_tool_logged
def process_single_file_tool(file_path: str) -> str:
    """
    Process a single Python file and extract metadata.

    Args:
        file_path: Path to the Python file relative to BASE_PATH

    Returns:
        JSON string with processing status
    """
    try:
        # Strip leading slashes/backslashes to avoid path issues
        file_path_clean = file_path.lstrip("/\\")
        result = ingest_single_file(file_path_clean, BASE_PATH)
        return json.dumps({"status": "success", "processed": result})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
@mcp_tool_logged
def parse_python_file_tool(file_path: str) -> str:
    """
    Parse a Python file and return its AST structure.

    Args:
        file_path: Path to the Python file relative to BASE_PATH

    Returns:
        JSON string representation of the AST
    """
    try:
        # Strip leading slashes/backslashes to avoid path issues
        file_path_clean = file_path.lstrip("/\\")
        ast_tree = parse_python_file(file_path_clean, BASE_PATH)
        # Convert AST to string representation
        ast_dump = json.dumps({"ast": str(ast_tree)})
        return ast_dump
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    if os.getenv("DOCKER_MODE") == "true":
        # Run with SSE transport for Docker networking
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8003"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        # Run with stdio for local development
        mcp.run(show_banner=False)
