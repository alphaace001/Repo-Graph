"""
Graph Query MCP Server - FastMCP implementation for knowledge graph traversal.
Provides tools for executing Cypher queries, finding entities, and analyzing relationships.
"""

import ast
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

# Setup Python paths before importing anything else
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add KG-Assignment to path
sys.path.insert(0, str(Path(__file__).parent))  # Add Graph_Query to path
sys.path.insert(0, str(Path(__file__).parent / "Utils"))  # Add Utils to path

try:
    import json
    from typing import Optional, List
    from fastmcp import FastMCP
    from Utils.query_service import GraphQueryService
finally:
    # Restore stdout
    sys.stdout = original_stdout

# Re-enable logging but only for CRITICAL level and to stderr
logging.disable(logging.NOTSET)
logging.basicConfig(level=logging.CRITICAL, format="", stream=sys.stderr)

# Initialize the MCP server
mcp = FastMCP("graph-query", version="1.0.0")

# Initialize the query service
query_service = GraphQueryService()


@mcp.tool()
def find_entity(name: str, entity_type: str = "") -> str:
    """
    Locate a class, function, or module by name.

    This tool searches the knowledge graph for entities matching the given name.
    Results can be filtered by type (Function, Class, Module).

    Args:
        name: Name or partial name of the entity to find
        entity_type: Optional entity type filter. Must be one of: "Function", "Class", or "Module"
                     If provided, only entities of this type will be returned.

    Returns:
        JSON string containing matched entities with their properties
    """
    try:
        # Normalize entity_type if provided
        if entity_type:
            entity_type = str(entity_type).strip()

        results = query_service.find_entity(name, entity_type)
        return json.dumps(
            {"status": "success", "count": len(results), "results": results}, default=str
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_dependencies(entity_name: str) -> str:
    """
    Find what an entity depends on.

    Returns all entities that the specified entity directly depends on
    (via DEPENDS_ON relationships).

    Args:
        entity_name: Name of the entity to analyze

    Returns:
        JSON string containing list of dependencies
    """
    try:
        results = query_service.get_dependencies(entity_name)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_name,
                "count": len(results),
                "dependencies": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_dependents(entity_name: str) -> str:
    """
    Find what depends on an entity.

    Returns all entities that depend on the specified entity
    (reverse DEPENDS_ON relationships).

    Args:
        entity_name: Name of the entity to analyze

    Returns:
        JSON string containing list of dependents
    """
    try:
        results = query_service.get_dependents(entity_name)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_name,
                "count": len(results),
                "dependents": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def trace_imports(module_name: str, max_depth: int = 5) -> str:
    """
    Follow import chain for a module.

    Traces all import paths starting from the specified module,
    showing the complete chain of imports up to max_depth levels.

    Args:
        module_name: Name of the module to trace imports for
        max_depth: Maximum depth for traversal (default: 5)

    Returns:
        JSON string containing import chains
    """
    try:
        if max_depth < 1 or max_depth > 10:
            max_depth = 5

        results = query_service.trace_imports(module_name, max_depth)
        return json.dumps(
            {
                "status": "success",
                "module": module_name,
                "max_depth": max_depth,
                "count": len(results),
                "import_chains": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def find_related(entity_name: str, relationship_type: str) -> str:
    """
    Get entities related by specified relationship type.

    Finds all entities connected to the specified entity via the given
    relationship type (e.g., IMPORTS, INHERITS_FROM, DECORATED_BY).
    Searches in both directions (incoming and outgoing relationships).

    Args:
        entity_name: Name of the entity
        relationship_type: Type of relationship (IMPORTS, INHERITS_FROM, DECORATED_BY, DEPENDS_ON, etc.)

    Returns:
        JSON string containing related entities
    """
    try:
        results = query_service.find_related(entity_name, relationship_type)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_name,
                "relationship_type": relationship_type,
                "count": len(results),
                "related_entities": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def execute_query(query: str, parameters: Optional[str] = None) -> str:
    """
    Run custom Cypher query with safety constraints.

    Allows execution of custom Cypher queries against the knowledge graph.
    Includes safety constraints to prevent destructive operations.
    Only READ operations are allowed (SELECT, MATCH, RETURN).

    Args:
        query: Cypher query string (must be read-only)
        parameters: Optional JSON string with query parameters

    Returns:
        JSON string containing query results

    Safety Constraints:
        - No DELETE, REMOVE, SET, CREATE, or MERGE operations
        - No system procedure calls (dbms.*, apoc.load.*)
        - Only read-only queries allowed
    """
    try:
        # Parse parameters if provided
        params = {}
        if parameters:
            try:
                params = json.loads(parameters)
            except json.JSONDecodeError:
                return json.dumps({"status": "error", "message": "Invalid JSON in parameters"})

        results = query_service.execute_custom_query(query, params)
        return json.dumps(
            {"status": "success", "count": len(results), "results": results}, default=str
        )
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def find_usage_patterns(entity_name: str) -> str:
    """
    Identify usage patterns across the codebase.

    Analyzes an entity and returns all the ways it's used throughout
    the codebase, including what depends on it, what it imports, and
    what uses it as a decorator or base class.

    Args:
        entity_name: Name of the entity to analyze

    Returns:
        JSON string containing comprehensive usage patterns
    """
    try:
        results = query_service.find_usage_patterns(entity_name)
        return json.dumps(
            {"status": "success", "entity": entity_name, "usage_patterns": results}, default=str
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_code_statistics() -> str:
    """
    Get statistics about the indexed codebase.

    Returns overall statistics about the knowledge graph, including
    counts of modules, functions, classes, and relationships.

    Returns:
        JSON string containing codebase statistics
    """
    try:
        results = query_service.get_code_statistics()
        return json.dumps({"status": "success", "statistics": results}, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
