"""
Module ingestion module - Creates Module nodes in the graph.
"""
from logger import setup_logger
from MCP.Indexer.Utils.graph_operations import GraphOperations

logger = setup_logger(__name__)


def ingest_module_to_graph(graph, current_file: str, code: str, module_docstring: str) -> str:
    """
    Build a Module node and return its element ID.
    
    Args:
        graph: Neo4jGraph instance
        current_file: Current file path
        code: Source code content
        module_docstring: Module-level docstring
    
    Returns:
        Element ID of the created module node
    """
    logger.debug("Building module node", extra={"extra_fields": {"file": current_file}})

    try:
        ops = GraphOperations(graph)
        
        # Create module node with content
        module_properties = {
            "name": current_file,
            "content": code,
        }
        module_id = ops.create_or_merge_node("Module", module_properties)

        if not module_id:
            raise ValueError(f"Failed to create module node for {current_file}")

        # Create docstring if it exists
        ops.create_docstring("Module", module_id, module_docstring)

        logger.info(
            "Module node created successfully",
            extra={"extra_fields": {"file": current_file, "module_id": module_id}},
        )
        return module_id

    except Exception as e:
        logger.error(
            f"Failed to create module node: {str(e)}",
            extra={"extra_fields": {"file": current_file}},
            exc_info=True,
        )
        raise
