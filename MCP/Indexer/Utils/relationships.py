"""
Relationships ingestion module - Creates relationships between entities in the graph.
"""
from typing import Dict, List

from logger import setup_logger

logger = setup_logger(__name__)


def create_function_to_function_relationships(
    graph, function_metadata: List[Dict], file_dict: Dict, source_file_path: str
) -> None:
    """
    Create DEPENDS_ON and DECORATED_BY relationships for functions.
    
    Args:
        graph: Neo4jGraph instance
        function_metadata: List of function metadata dictionaries
        file_dict: Dictionary mapping module names to file paths
        source_file_path: The current source file path
    """
    for fn in function_metadata:
        # Create DEPENDS_ON relationships for function calls
        calls = fn.get("calls", {})
        codebase_imports = calls.get("codebase", [])
        import_and_fn = {}
        for imp in codebase_imports:
            if "." not in imp:
                continue
            lib, fn_name = imp.rsplit(".", 1)
            import_and_fn[lib] = fn_name

        # Creating relationships for calls
        for lib, fn_name in import_and_fn.items():
            graph.query(
                """
                MATCH (source_module:Module {name: $source_module})
                MATCH (source_module)-[:CONTAINS]->(f:Function {name: $fn_name})
                WHERE ($parent IS NULL AND f.parent_function IS NULL)
                OR ($parent IS NOT NULL AND f.parent_function = $parent)
                
                MATCH (m:Module {name: $target_module})
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
                WHERE target_func.parent_function IS NULL
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
                
                WITH f, target_func, target_class
                WHERE target_func IS NOT NULL OR target_class IS NOT NULL
                
                FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (f)-[:DEPENDS_ON]->(target_func)
                )
                
                FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (f)-[:DEPENDS_ON]->(target_class)
                )
                """,
                {
                    "source_module": source_file_path,
                    "fn_name": fn["name"],
                    "parent": fn.get("parent_function"),
                    "target_module": file_dict[lib],
                    "symbol_name": fn_name,
                },
            )

        # Create DECORATED_BY relationships for decorators
        decorators = fn.get("decorators", [])
        for dec in decorators:
            importing_from = dec.get("importing_from")
            if not importing_from or "." not in importing_from:
                continue

            module_path, symbol_name = importing_from.rsplit(".", 1)
            target_module = file_dict.get(module_path)

            if not target_module:
                continue

            graph.query(
                """
                MATCH (source_module:Module {name: $source_module})
                MATCH (source_module)-[:CONTAINS]->(f:Function {name: $fn_name})
                WHERE ($parent IS NULL AND f.parent_function IS NULL)
                OR ($parent IS NOT NULL AND f.parent_function = $parent)
                
                MATCH (m:Module {name: $target_module})
                
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
                    "source_module": source_file_path,
                    "fn_name": fn["name"],
                    "parent": fn.get("parent_function"),
                    "target_module": target_module,
                    "symbol_name": symbol_name,
                },
            )


def create_class_to_class_relationships(
    graph, class_metadata: List[Dict], file_dict: Dict, source_file_path: str
) -> None:
    """
    Process class metadata to create:
    1. INHERITS_FROM relationships for base classes
    2. Call create_function_to_function_relationships for class methods
    
    Args:
        graph: Neo4jGraph instance
        class_metadata: List of class metadata dictionaries
        file_dict: Dictionary mapping module names to file paths
        source_file_path: The current source file path
    """
    for cls in class_metadata:
        class_name = cls["name"]

        # Create INHERITS_FROM relationships for base classes
        base_classes = cls.get("base_classes", [])
        for base in base_classes:
            base_name = base.get("name")
            importing_from = base.get("importing_from")

            if not importing_from or not base_name:
                continue

            # Parse importing_from to get module path and symbol name
            if "." in importing_from:
                module_path, symbol_name = importing_from.rsplit(".", 1)
            else:
                module_path = importing_from
                symbol_name = importing_from

            # Look up the target file path
            target_file = file_dict.get(module_path)

            if not target_file:
                continue

            # Create INHERITS_FROM relationship
            graph.query(
                """
                MATCH (source_module:Module {name: $source_file})
                MATCH (source_module)-[:CONTAINS]->(child_class:Class {name: $child_name})
                
                MATCH (target_module:Module {name: $target_file})
                MATCH (target_module)-[:CONTAINS]->(parent_class:Class {name: $parent_name})
                
                MERGE (child_class)-[:INHERITS_FROM]->(parent_class)
                """,
                {
                    "source_file": source_file_path,
                    "child_name": class_name,
                    "target_file": target_file,
                    "parent_name": symbol_name,
                },
            )

        # Process methods with function_to_function_relationships
        methods = cls.get("methods", [])
        if methods:
            create_function_to_function_relationships(
                graph, methods, file_dict, source_file_path
            )
