"""
Cypher query utilities for creating relationships in Neo4j graph.
"""
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from graph_operations import GraphOperations


def create_import_relationships(
    current_file: str, codebase_imports: List[Dict], repo_modules: Dict, graph
) -> None:
    """
    Create IMPORTS relationships from current module to imported modules.

    Args:
        current_file: The current module file path (e.g., "fastapi/routing.py")
        codebase_imports: List of codebase imports with "module" key
        repo_modules: Dictionary mapping module paths to file paths
        graph: Neo4jGraph instance
    """
    ops = GraphOperations(graph)
    
    for imp in codebase_imports:
        module_name = imp.get("module")

        if not module_name:
            continue

        # Get the target file path from repo_modules
        target_file = repo_modules.get(module_name)

        if not target_file:
            continue

        # Create IMPORTS relationship using GraphOperations
        ops.create_import_relationship(current_file, target_file)
