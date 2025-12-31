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
    Search the code knowledge graph for an entity by name, optionally filtered
    by entity type, and return matching nodes with metadata.

    This tool supports lookup of:
    Function, Class, Module, Docstring, Method, and Parameter nodes.

    Args:
        name: Full or partial entity name to search for.
        entity_type: Optional label filter. Must be one of:
                    "Function", "Class", "Module", "Docstring", "Method", "Parameter".

    Returns:
        A list of matched entities (max 20), each containing:
            - name: entity name
            - type: primary node label
            - properties: full node properties
            - id: Neo4j elementId
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
def get_dependencies(entity_id: str) -> str:
    """
    Retrieve the outgoing `DEPENDS_ON` relationships for an entity in the
    code knowledge graph, identified by its Neo4j `elementId`.

    Args:
        entity_id: Neo4j elementId of the source entity node
                (Function, Class, or Method).

    Returns:
        A list of dependency records, each containing:
        - source_name: name of the entity that owns the dependency
        - source_type: label of the source node
        - relationship: relationship type ("DEPENDS_ON")
        - target_name: name of the dependency target
        - target_type: label of the target node
        - target_id: Neo4j elementId of the target node
    """
    try:
        results = query_service.get_dependencies(entity_id)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_id,
                "count": len(results),
                "dependencies": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def get_dependents(entity_id: str) -> str:
    """
    Retrieve the incoming `DEPENDS_ON` relationships for an entity in the
    code knowledge graph, returning the entities that depend on it.

    Args:
        entity_id: Neo4j elementId of the target entity node
                (Function, Class, or Method).

    Returns:
        A list of dependent records, each containing:
            - source_name: name of the dependent entity
            - source_type: label of the dependent node
            - source_id: Neo4j elementId of the dependent node
            - relationship: relationship type ("DEPENDS_ON")
            - target_name: name of the entity being depended on
            - target_type: label of the target node
    """
    try:
        results = query_service.get_dependents(entity_id)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_id,
                "count": len(results),
                "dependents": results,
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def trace_imports(module_name: str, max_depth: int = 3) -> str:
    """
    Follow import chain for a module.

    Traces all import paths starting from the specified module,
    showing the complete chain of imports up to max_depth levels.

    Args:
        module_name: Name of the module to trace imports for
        max_depth: Maximum depth for traversal (default: 3)

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
def find_related(entity_id: str, relationship_type: str) -> str:
    """
    Find entities that are connected to a given node by a specific
    relationship type in the code knowledge graph. Supports both
    outgoing and incoming relationship directions.

     Args:
         entity_id: Neo4j elementId of the source or target entity.
         relationship_type: Relationship label to query. Must be one of:
             "CONTAINS", "DEPENDS_ON", "DOCUMENTED_BY",
             "HAS_PARAMETER", "IMPORTS", "INHERITS_FROM",
             "DECORATED_BY".

     Returns:
         A list of related entities, each containing:
             - source_name / source_type
             - target_name / target_type
             - target_id (Neo4j elementId)
             - relationship (requested relationship type)
    """
    try:
        results = query_service.find_related(entity_id, relationship_type)
        return json.dumps(
            {
                "status": "success",
                "entity": entity_id,
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
    mcp.run(show_banner=False)
