"""
Analyst MCP Server - FastMCP implementation for deep code understanding and pattern analysis.
Provides tools for analyzing functions, classes, design patterns, code snippets, and implementations.
"""

import sys
from pathlib import Path

# Setup Python paths for local modules BEFORE any imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add KG-Assignment to path
sys.path.insert(0, str(Path(__file__).parent))  # Add Analyst to path

import json
from fastmcp import FastMCP
from logger import get_mcp_safe_logger, mcp_tool_logged, configure_mcp_logging
from Utils.analysis_service import CodeAnalysisService

# Configure MCP-safe logging
configure_mcp_logging()
logger = get_mcp_safe_logger(__name__)

# Initialize the MCP server
mcp = FastMCP("analyst", version="1.0.0")

# Initialize the analysis service
# Database connection is handled internally via Database.Neo4j
try:
    analysis_service = CodeAnalysisService()
    logger.info("Analysis service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize analysis service: {str(e)}")
    sys.exit(1)


@mcp.tool()
@mcp_tool_logged
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
@mcp_tool_logged
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
@mcp_tool_logged
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
    import os
    
    if os.getenv("DOCKER_MODE") == "true":
        # Run with SSE transport for Docker networking
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8001"))
        mcp.run(transport="sse", host=host, port=port)
    else:
        # Run with stdio for local development
        mcp.run(show_banner=False)
