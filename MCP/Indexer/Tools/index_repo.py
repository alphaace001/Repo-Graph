"""
Main ingestion orchestrator - Coordinates the graph ingestion pipeline.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Utils.utils import discover_py_files, convert_file_paths_to_modules
from Utils.cypherquery_utils import create_import_relationships
from Utils.file_processor import process_single_file
from Utils.relationships import (
    create_function_to_function_relationships,
    create_class_to_class_relationships,
)

from logger import LogContext, log_with_context
from Database.Neo4j.initialise import graph, logger
import os
from dotenv import load_dotenv

load_dotenv()
BASE_PATH = os.getenv("BASE_PATH", "D:\\KGassign\\fastapi")


def ingest_all_files(repo_path: str) -> None:
    """Ingest all Python files from the codebase into the graph."""
    # repo_path is already the full path to search
    discovery_path = repo_path
    
    files = discover_py_files(discovery_path)
    file_dict = convert_file_paths_to_modules(files)
    with LogContext(logger=logger) as correlation_id:
        logger.info(
            "Starting batch file ingestion",
            extra={"extra_fields": {"total_files": len(files), "path": discovery_path}},
        )

        success_count = 0
        error_count = 0
        errors = []
        all_imports = {}  # Store imports for each file
        all_functions = {}  # Store function metadata for each file
        all_classes = {}  # Store class metadata for each file

        # Phase 1: Process individual files
        for idx, file_path in enumerate(files, 1):
            with LogContext(logger=logger):  # New correlation ID for each file
                try:
                    codebase_imports, function_metadata, class_metadata = (
                        process_single_file(file_path, discovery_path, graph, file_dict)
                    )
                    all_imports[file_path] = codebase_imports
                    all_functions[file_path] = function_metadata
                    all_classes[file_path] = class_metadata
                    success_count += 1
                    log_with_context(
                        logger,
                        logging.INFO,
                        "File completed",
                        progress=f"{idx}/{len(files)}",
                        file=file_path,
                        status="success",
                    )
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    errors.append({"file": file_path, "error": error_msg})
                    log_with_context(
                        logger,
                        logging.ERROR,
                        "File failed",
                        progress=f"{idx}/{len(files)}",
                        file=file_path,
                        status="error",
                        error=error_msg,
                    )
                    continue

        logger.info(
            "Batch ingestion completed",
            extra={
                "extra_fields": {
                    "total_files": len(files),
                    "success_count": success_count,
                    "error_count": error_count,
                    "success_rate": f"{(success_count/len(files)*100):.2f}%",
                }
            },
        )

        # Phase 2: Create import relationships
        logger.info(
            "Creating module import relationships",
            extra={"extra_fields": {"total_files": len(all_imports)}},
        )
        relationship_count = 0
        for file_path, codebase_imports in all_imports.items():
            try:
                create_import_relationships(
                    file_path, codebase_imports, file_dict, graph
                )
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

        logger.info(
            "Import relationships creation completed",
            extra={"extra_fields": {"total_relationships": relationship_count}},
        )

        # Phase 3: Create function-to-function relationships
        logger.info(
            "Creating function-to-function relationships",
            extra={"extra_fields": {"total_files": len(all_functions)}},
        )
        for file_path, function_metadata in all_functions.items():
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

        logger.info("Function-to-function relationships creation completed")

        # # Phase 4: Create class-to-class relationships
        logger.info(
            "Creating class-to-class relationships",
            extra={"extra_fields": {"total_files": len(all_classes)}},
        )
        for file_path, class_metadata in all_classes.items():
            try:
                create_class_to_class_relationships(
                    graph, class_metadata, file_dict, file_path
                )
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

        logger.info("Class-to-class relationships creation completed")
        logger.warning(
            f"Encountered {error_count} errors during ingestion",
            extra={"extra_fields": {"errors": errors[:10]}},
        )  # Log first 10 errors


if __name__ == "__main__":
    ingest_all_files()
