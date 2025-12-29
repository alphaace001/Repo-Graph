import sys
from pathlib import Path
from typing import Dict, Callable

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import setup_logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from graph_operations import GraphOperations

logger = setup_logger(__name__)


def _build_function_index(functions: list) -> Dict:
    """
    Build an index of functions by (name, parent_function) key.
    
    Args:
        functions: List of function metadata dictionaries
    
    Returns:
        Dictionary indexed by (name, parent_function) tuple
    """
    index = {}
    for fn in functions:
        key = (fn["name"], fn.get("parent_function"))
        index.setdefault(key, []).append(fn)
    return index


def _merge_function_node(graph, fn):
    """Create or merge a Function node in the graph and return its ID."""
    parent = fn.get("parent_function")

    if parent is None:
        # Top-level function
        result = graph.query(
            """
            MERGE (f:Function {name: $name})
            SET f.start_line = $start,
                f.end_line = $end,
                f.parent_function = NULL
            RETURN elementId(f) as func_id
            """,
            {
                "name": fn["name"],
                "start": fn["start_line"],
                "end": fn["end_line"],
            },
        )
    else:
        # Nested function
        result = graph.query(
            """
            MERGE (f:Function {
              name: $name,
              parent_function: $parent
            })
            SET f.start_line = $start,
                f.end_line = $end
            RETURN elementId(f) as func_id
            """,
            {
                "name": fn["name"],
                "parent": parent,
                "start": fn["start_line"],
                "end": fn["end_line"],
            },
        )

    return result[0]["func_id"]


def _create_docstring_node(graph, func_id, docstring):
    """Create a Docstring node and link it to the function."""
    if not docstring or not docstring.strip():
        return

    graph.query(
        """
        MATCH (f:Function)
        WHERE elementId(f) = $func_id

        MERGE (d:Docstring {name: $doc_name})
        SET d.content = $doc_text

        MERGE (f)-[:DOCUMENTED_BY]->(d)
        """,
        {
            "func_id": func_id,
            "doc_name": f"func_{func_id}_docstring",
            "doc_text": docstring,
        },
    )


def _create_parameter_nodes(graph, func_id, args):
    """Create Parameter nodes for function arguments."""
    for arg in args:
        kv_pair = f"{arg['name']}={arg.get('annotation_display') or ''}"

        graph.query(
            """
            MATCH (f:Function)
            WHERE elementId(f) = $func_id

            MERGE (p:Parameter {name: $param_name})

            // store list of key=value strings
            SET p.pairs = coalesce(p.pairs, []) + $pair

            MERGE (f)-[:HAS_PARAMETER]->(p)
            """,
            {
                "func_id": func_id,
                "param_name": f"func_{func_id}_parameter",
                "pair": [kv_pair],
            },
        )


def _create_decorator_relationships(graph, func_id, decorators, file_dict):
    """Create DECORATED_BY relationships for function decorators."""
    for dec in decorators:
        importing_from = dec["importing_from"]
        module_path, symbol_name = importing_from.rsplit(".", 1)
        module_path = file_dict.get(module_path)

        graph.query(
            """
            MATCH (f:Function)
            WHERE elementId(f) = $func_id
            
            MATCH (m:Module {name: $module_path})
            
            OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
            WHERE target_func.parent_function IS NULL
            
            OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
            
            WITH f, target_func, target_class
            WHERE target_func IS NOT NULL OR target_class IS NOT NULL
            
            FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                MERGE (f)-[:DECORATED_BY]->(target_func)
            )
            
            FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                MERGE (f)-[:DECORATED_BY]->(target_class)
            )
            """,
            {
                "func_id": func_id,
                "module_path": module_path,
                "symbol_name": symbol_name,
            },
        )


def _create_depends_on_relationships(
    ops: GraphOperations, func_id: str, fn: Dict, index: Dict, ensure_function: Callable, file_dict: Dict
) -> None:
    """
    Create DEPENDS_ON relationships for nested functions.
    
    Args:
        ops: GraphOperations instance
        func_id: Element ID of parent function
        fn: Function metadata dictionary
        index: Function index by (name, parent_function)
        ensure_function: Callback to ensure a function is processed
        file_dict: Dictionary mapping module names to file paths
    """
    for dep_name in fn.get("depends", []):
        dep_key = (dep_name, fn["name"])
        for child in index.get(dep_key, []):
            child_func_id = ensure_function(child, file_dict)
            ops.create_relationship("Function", func_id, "DEPENDS_ON", "Function", child_func_id)


def _create_module_function_relationship(graph, func_id, module_id):
    """Create MODULE-[:CONTAINS]->FUNCTION relationship for top-level functions."""
    graph.query(
        """
        MATCH (f:Function)
        WHERE elementId(f) = $func_id
        
        MATCH (m:Module)
        WHERE elementId(m) = $module_id
        
        MERGE (m)-[:CONTAINS]->(f)
        """,
        {
            "func_id": func_id,
            "module_id": module_id,
        },
    )


def ingest_functions_to_graph(functions: list, graph, file_dict: dict, module_id: str) -> None:
    """
    Ingest function metadata into the graph database.
    
    Args:
        functions: List of function metadata dictionaries
        graph: Neo4jGraph instance
        file_dict: Dictionary mapping module names to file paths
        module_id: Element ID of the parent module
    """
    logger.debug("Starting function ingestion", extra={'extra_fields': {'function_count': len(functions)}})
    
    ops = GraphOperations(graph)
    index = _build_function_index(functions)
    processed = set()
    func_id_cache = {}

    def ensure_function(fn: Dict, file_dict: Dict) -> str:
        """
        Ensure a function exists in the graph, processing it if not already done.
        
        Args:
            fn: Function metadata dictionary
            file_dict: Dictionary mapping module names to file paths
        
        Returns:
            Element ID of the function node
        """
        key = (fn["name"], fn.get("parent_function"))
        if key in processed:
            return func_id_cache.get(key)

        processed.add(key)
        
        logger.debug("Processing function", 
                    extra={'extra_fields': {
                        'function': fn["name"],
                        'parent': fn.get("parent_function"),
                        'is_nested': fn.get("parent_function") is not None
                    }})

        try:
            # Create function node using GraphOperations
            fn_properties = {
                "name": fn["name"],
                "start_line": fn["start_line"],
                "end_line": fn["end_line"],
                "parent_function": fn.get("parent_function"),
            }
            func_id = ops.create_or_merge_node("Function", fn_properties)
            func_id_cache[key] = func_id

            # Create module-function relationship for top-level functions only
            if fn.get("parent_function") is None:
                ops.create_contains_relationship("Module", module_id, "Function", func_id)

            # Create docstring
            ops.create_docstring("Function", func_id, fn.get("docstring"))

            # Create parameters
            for arg in fn.get("args", []):
                kv_pair = f"{arg['name']}={arg.get('annotation_display') or ''}"
                ops.create_parameter_node("Function", func_id, f"func_{func_id}_parameter", kv_pair)

            # Create depends_on relationships
            _create_depends_on_relationships(
                ops, func_id, fn, index, ensure_function, file_dict
            )
            
            logger.debug("Function processed successfully", 
                        extra={'extra_fields': {'function': fn["name"]}})

            return func_id
            
        except Exception as e:
            logger.error(f"Failed to process function: {str(e)}", 
                        extra={'extra_fields': {'function': fn["name"]}}, 
                        exc_info=True)
            raise

    # Process all functions
    for fn in functions:
        ensure_function(fn, file_dict)
    
    logger.info("Function ingestion completed", 
               extra={'extra_fields': {
                   'total_functions': len(functions),
                   'processed_count': len(processed)
               }})
