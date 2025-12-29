import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import setup_logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from graph_operations import GraphOperations

logger = setup_logger(__name__)


def _create_class_node(graph, cls):
    """Creates a Class node in the graph and returns its ID."""
    result = graph.query(
        """
        MERGE (c:Class {name: $name})
        SET c.start_line = $start,
            c.end_line = $end
        RETURN elementId(c) as class_id
        """,
        {
            "name": cls["name"],
            "start": cls["start_line"],
            "end": cls["end_line"],
        },
    )
    return result[0]["class_id"]


def _create_docstring_node(graph, entity_id, entity_type, docstring):
    """Creates a Docstring node and links it to the given entity."""
    if not docstring or not docstring.strip():
        return

    graph.query(
        f"""
        MATCH (e:{entity_type})
        WHERE elementId(e) = $entity_id
        MERGE (d:Docstring {{name: $doc_name}})
        SET d.content = $doc_text
        MERGE (e)-[:DOCUMENTED_BY]->(d)
        """,
        {
            "entity_id": entity_id,
            "doc_name": f"{entity_type.lower()}_{entity_id}_docstring",
            "doc_text": docstring,
        },
    )


def _create_decorator_relationship(graph, entity_id, entity_type, decorator, file_dict):
    """Creates a DECORATED_BY relationship between an entity and a decorator."""
    importing_from = decorator["importing_from"]
    module_path, symbol_name = importing_from.rsplit(".", 1)
    module_path = file_dict.get(module_path)

    entity_match = "c:Class" if entity_type == "Class" else "meth:Method"
    entity_var = "c" if entity_type == "Class" else "meth"

    graph.query(
        f"""
        MATCH ({entity_match})
        WHERE elementId({entity_var}) = $entity_id
        
        MATCH (m:Module {{name: $module_path}})
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {{name: $symbol_name}})
        WHERE target_func.parent_function IS NULL
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {{name: $symbol_name}})
        
        WITH {entity_var}, target_func, target_class
        WHERE target_func IS NOT NULL OR target_class IS NOT NULL
        
        FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
            MERGE ({entity_var})-[:DECORATED_BY]->(target_func)
        )
        
        FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
            MERGE ({entity_var})-[:DECORATED_BY]->(target_class)
        )
        """,
        {
            "entity_id": entity_id,
            "module_path": module_path,
            "symbol_name": symbol_name,
        },
    )


def _create_method_node(graph, class_id, class_name, method):
    """Creates a Method node in the graph and returns its ID."""
    method_result = graph.query(
        """
        MATCH (c:Class)
        WHERE elementId(c) = $class_id

        MERGE (m:Method {
          name: $name,
          parent_class: $class_name
        })
        SET m.start_line = $start,
            m.end_line = $end

        MERGE (c)-[:CONTAINS]->(m)
        RETURN elementId(m) as method_id
        """,
        {
            "class_id": class_id,
            "class_name": class_name,
            "name": method["name"],
            "start": method["start_line"],
            "end": method["end_line"],
        },
    )
    return method_result[0]["method_id"]


def _create_parameter_nodes(graph, method_id, args):
    """Creates Parameter nodes for method arguments."""
    for arg in args:
        kv_pair = f"{arg['name']}={arg.get('annotation_display') or ''}"

        graph.query(
            """
            MATCH (m:Method)
            WHERE elementId(m) = $method_id

            MERGE (p:Parameter {
              name: $param_group
            })

            SET p.pairs = coalesce(p.pairs, []) + $pair

            MERGE (m)-[:HAS_PARAMETER]->(p)
            """,
            {
                "method_id": method_id,
                "param_group": f"method_{method_id}_parameters",
                "pair": [kv_pair],
            },
        )


def _ingest_class_methods(ops: GraphOperations, class_id: str, class_name: str, methods: list, file_dict: dict) -> None:
    """
    Ingest all methods of a class into the graph.
    
    Args:
        ops: GraphOperations instance
        class_id: Element ID of the parent class
        class_name: Name of the parent class
        methods: List of method metadata dictionaries
        file_dict: Dictionary mapping module names to file paths
    """
    for method in methods:
        method_id = _create_method_node(ops.graph, class_id, class_name, method)

        # Create method docstring
        ops.create_docstring("Method", method_id, method.get("docstring"))

        # Create parameter nodes
        _create_parameter_nodes(ops.graph, method_id, method.get("args", []))

        # Create decorator relationships
        for dec in method.get("decorators", []):
            _create_decorator_relationship(ops.graph, method_id, "Method", dec, file_dict)


def _create_module_class_relationship(graph, class_id, module_id):
    """Create MODULE-[:CONTAINS]->CLASS relationship."""
    graph.query(
        """
        MATCH (c:Class)
        WHERE elementId(c) = $class_id
        
        MATCH (m:Module)
        WHERE elementId(m) = $module_id
        
        MERGE (m)-[:CONTAINS]->(c)
        """,
        {
            "class_id": class_id,
            "module_id": module_id,
        },
    )


def ingest_classes_to_graph(classes: list, graph, file_dict: dict, module_id: str) -> None:
    """
    Ingest class metadata into the graph database.
    
    Creates Class, Method, Docstring, Parameter nodes and relationships
    from extracted class metadata.
    
    Args:
        classes: List of class metadata dictionaries
        graph: Neo4jGraph instance
        file_dict: Dictionary mapping module names to file paths
        module_id: Element ID of the parent module
    """
    logger.debug("Starting class ingestion", extra={'extra_fields': {'class_count': len(classes)}})
    
    ops = GraphOperations(graph)
    
    for cls in classes:
        try:
            logger.debug("Processing class", extra={'extra_fields': {'class': cls["name"]}})
            
            # Create Class node using GraphOperations
            class_properties = {
                "name": cls["name"],
                "start_line": cls["start_line"],
                "end_line": cls["end_line"],
            }
            class_id = ops.create_or_merge_node("Class", class_properties)

            # Create class docstring
            ops.create_docstring("Class", class_id, cls.get("docstring"))

            # Ingest all methods
            method_count = len(cls.get("methods", []))
            _ingest_class_methods(ops, class_id, cls["name"], cls.get("methods", []), file_dict)
            
            logger.debug("Methods ingested", 
                        extra={'extra_fields': {
                            'class': cls["name"], 
                            'method_count': method_count
                        }})

            # Create module-class relationship
            ops.create_contains_relationship("Module", module_id, "Class", class_id)
            
            logger.debug("Class processed successfully", 
                        extra={'extra_fields': {'class': cls["name"]}})
            
        except Exception as e:
            logger.error(f"Failed to process class: {str(e)}", 
                        extra={'extra_fields': {'class': cls["name"]}}, 
                        exc_info=True)
            raise
    
    logger.info("Class ingestion completed", 
               extra={'extra_fields': {'total_classes': len(classes)}})
