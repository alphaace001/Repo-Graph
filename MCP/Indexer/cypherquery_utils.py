def create_import_relationships(
    current_file: str, codebase_imports: list[dict], repo_modules: dict, graph
):
    """
    Creates IMPORTS relationships from current module to imported modules.

    Args:
        current_file: The current module file path (e.g., "fastapi/routing.py")
        codebase_imports: List of codebase imports with "module" key
        repo_modules: Dictionary mapping module paths to file paths
        graph: Neo4jGraph instance
    """
    for imp in codebase_imports:
        module_name = imp.get("module")

        if not module_name:
            continue

        # Get the target file path from repo_modules
        target_file = repo_modules.get(module_name)

        if not target_file:
            continue

        # Create IMPORTS relationship
        graph.query(
            """
            MATCH (source:Module {name: $source_file})
            MATCH (target:Module {name: $target_file})
            MERGE (source)-[:IMPORTS]->(target)
            """,
            {
                "source_file": current_file,
                "target_file": target_file,
            },
        )
