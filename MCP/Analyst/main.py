"""
Analyst MCP Server - FastMCP implementation for deep code understanding and pattern analysis.
Provides tools for analyzing functions, classes, design patterns, code snippets, and implementations.
"""

import sys
import logging
import io
from pathlib import Path

# Suppress ALL logging output that interferes with MCP protocol communication
logging.disable(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

# Capture stdout during imports to suppress logging messages
captured_output = io.StringIO()
original_stdout = sys.stdout
sys.stdout = captured_output

# Setup Python paths for local modules
sys.path.insert(0, str(Path(__file__).parent))  # Add Analyst to path

try:
    import json
    from typing import Optional, List
    from fastmcp import FastMCP
    from Utils.analysis_service import CodeAnalysisService
    from Utils.db_connection import Neo4jConnection
finally:
    # Restore stdout
    sys.stdout = original_stdout

# Re-enable logging but only for CRITICAL level and to stderr
logging.disable(logging.NOTSET)
logging.basicConfig(level=logging.CRITICAL, format="", stream=sys.stderr)

# Initialize the MCP server
mcp = FastMCP("analyst", version="1.0.0")

# Initialize database connection FIRST, before service initialization
# print("Establishing Neo4j connection...", file=sys.stderr)
try:
    db_connection = Neo4jConnection()
    # print("✓ Successfully connected to Neo4j database", file=sys.stderr)
except Exception as e:
    error_msg = f"✗ Failed to connect to Neo4j: {str(e)}"
    # print(error_msg, file=sys.stderr)
    sys.exit(1)

# Initialize the analysis service with the established connection
analysis_service = CodeAnalysisService(db_connection)


@mcp.tool()
def analyze_function(function_id: str, include_calls: bool = True) -> str:
    """
    Analyze a function node in the code knowledge graph and return its metadata,
    structural context, relationships, and surrounding source code snippet.

    Given a function's Neo4j `elementId`, this tool returns:
    - file location (module, start/end lines, LOC)
    - docstring
    - parameters (flattened list of "name=type")
    - functions or entities it depends on (`DEPENDS_ON`)
    - functions or entities that call it (`called_by`)
    - optional detailed dependency edges (via `get_dependencies`)
    - a contextual code excerpt from the module

    Args:
        function_id: Neo4j elementId of the function node.
        include_calls: If True, include expanded dependency edges.
        context_lines: Number of context lines around the function body.

    Returns:
        Structured JSON object describing the function's definition,
        relationships, and code context, or an error if not found.
    """

    try:
        results = analysis_service.analyze_function(function_id, include_calls)
        return json.dumps(
            {"status": "success", "function": function_id, "analysis": results},
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def analyze_class(class_id: str, include_methods: bool = True) -> str:
    """
    Analyze a class node in the code knowledge graph and return its metadata,
    structure, inheritance relationships, methods, and surrounding source code snippet.

    Given a class Neo4j `elementId`, this tool returns:
    - file location (module, start/end lines, LOC)
    - docstring
    - methods defined inside the class (with line metadata)
    - parent classes (`INHERITS_FROM`)
    - subclasses (reverse inheritance)
    - optional detailed dependency edges (via `get_dependencies`)
    - a contextual code excerpt from the module

    Args:
        class_id: Neo4j elementId of the class node.
        include_calls: If True, include expanded dependency edges.
        context_lines: Number of context lines around the class definition.

    Returns:
        Structured JSON object describing the class, its methods,
        inheritance relations, and code context, or an error if not found.
    """
    try:
        results = analysis_service.analyze_class(class_id, include_methods)
        return json.dumps(
            {"status": "success", "class": class_id, "analysis": results}, default=str
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_code_snippet(entity_id: str, context_lines: int = 5) -> str:
    """
    Extract code snippet with surrounding context.

    This tool retrieves the source code of an entity (function, class, method)
    along with surrounding context for better understanding.

    Args:
        entity_id: Neo4j elementId of the class node. (function, class, or method)
        context_lines: Number of lines of context before and after (default: 5)

    Returns:
        JSON string containing the code snippet with file location and line numbers
    """
    try:
        results = analysis_service.get_code_snippet(entity_id, context_lines)
        return json.dumps(
            {"status": "success", "entity": entity_id, "snippet": results},
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    mcp.run(show_banner=False)
