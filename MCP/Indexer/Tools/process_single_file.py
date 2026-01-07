"""
Wrapper module for processing a single Python file.
Provides a simplified interface for file processing.
"""

import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

from MCP.Indexer.Utils.file_processor import process_single_file
from MCP.Indexer.Utils.utils import discover_py_files, convert_file_paths_to_modules
from MCP.Indexer.Utils.cypherquery_utils import create_import_relationships
from MCP.Indexer.Utils.relationships import (
    create_function_to_function_relationships,
    create_class_to_class_relationships,
)
from Database.Neo4j.initialise import graph, logger

load_dotenv()
BASE_PATH = os.getenv("BASE_PATH", "D:\\KGassign\\fastapi")


def ingest_single_file(file_path: str, base_path: str = BASE_PATH) -> bool:
    """
    Wrapper function to process a single Python file and extract metadata.

    Args:
        file_path: Path to the Python file to process
        base_path: Base path for file discovery (default: FastAPI codebase path)

    Returns:
        Tuple of (codebase_imports, function_metadata, class_metadata)
            - codebase_imports: List of import dictionaries for the file
            - function_metadata: List of function metadata extracted from the file
            - class_metadata: List of class metadata extracted from the file

    Raises:
        FileNotFoundError: If the file_path does not exist
        Exception: If there's an error during file processing or AST parsing
    """
    # Initialize file_dict by discovering Python files in base_path
    file_dict = None
    if file_dict is None:
        logger.debug("Auto-generating file_dict from base_path")
        files = discover_py_files(base_path)
        if files:
            file_dict = convert_file_paths_to_modules(files)
        else:
            logger.warning(
                "No Python files found in base_path for file_dict generation",
                extra={"extra_fields": {"base_path": base_path}},
            )
            file_dict = {}

    logger.info(
        "Processing single file via wrapper",
        extra={"extra_fields": {"file": file_path, "base_path": base_path}},
    )

    # Call the core file processor
    try:
        codebase_imports, function_metadata, class_metadata = process_single_file(
            file_path, base_path, graph, file_dict
        )
    except Exception as e:
        logger.error(
            f"Error processing file {file_path}: {str(e)}",
            extra={"extra_fields": {"file": file_path}},
            exc_info=True,
        )
        return False

    # Initialize relationship count
    relationship_count = 0

    # Phase 2: Create import relationships
    logger.info(
        "Creating module import relationships",
        extra={"extra_fields": {"file": file_path}},
    )
    try:
        create_import_relationships(file_path, codebase_imports, file_dict, graph)
        relationship_count += len(codebase_imports)
        logger.debug(
            "Import relationships created",
            extra={
                "extra_fields": {
                    "file": file_path,
                    "import_count": len(codebase_imports),
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Failed to create import relationships: {str(e)}",
            extra={"extra_fields": {"file": file_path}},
            exc_info=True,
        )
        return False

    logger.info(
        "Import relationships creation completed",
        extra={"extra_fields": {"total_relationships": relationship_count}},
    )

    # Phase 3: Create function-to-function relationships
    logger.info(
        "Creating function-to-function relationships",
        extra={"extra_fields": {"total_files": len(function_metadata)}},
    )
    try:
        create_function_to_function_relationships(
            graph, function_metadata, file_dict, file_path
        )
        logger.debug(
            "Function relationships created",
            extra={
                "extra_fields": {
                    "file": file_path,
                    "function_count": len(function_metadata),
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Failed to create function relationships: {str(e)}",
            extra={"extra_fields": {"file": file_path}},
            exc_info=True,
        )
        return False
    logger.info("Function-to-function relationships creation completed")

    # Phase 4: Create class-to-class relationships
    logger.info(
        "Creating class-to-class relationships",
        extra={"extra_fields": {"file": file_path}},
    )
    try:
        create_class_to_class_relationships(graph, class_metadata, file_dict, file_path)
        logger.debug(
            "Class relationships created",
            extra={
                "extra_fields": {
                    "file": file_path,
                    "class_count": len(class_metadata),
                }
            },
        )
    except Exception as e:
        logger.error(
            f"Failed to create class relationships: {str(e)}",
            extra={"extra_fields": {"file": file_path}},
            exc_info=True,
        )
        return False

    logger.info("Class-to-class relationships creation completed")

    # Return the extracted metadata for potential further processing
    return True


if __name__ == "__main__":
    # Example usage: process a single file
    test_file = "fastapi/main.py"
    try:
        imports, functions, classes = process_single_file(test_file)
        print(f"Successfully processed {test_file}")
        print(f"  - Imports: {len(imports)}")
        print(f"  - Functions: {len(functions)}")
        print(f"  - Classes: {len(classes)}")
    except Exception as e:
        print(f"Error processing file: {e}")
