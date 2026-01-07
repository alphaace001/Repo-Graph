"""
File processor module - Processes individual Python files and extracts metadata.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from logger import setup_logger, log_with_context

from MCP.Indexer.Utils.utils import load_code
from MCP.Indexer.Utils.import_utils import collect_grouped_imports, classify_imports
from MCP.Indexer.Utils.functions.function_utils import build_codebase_symbol_lookup
from MCP.Indexer.Utils.functions.function_metadata import extract_function_metadata
from MCP.Indexer.Utils.functions.ingest_function_to_graph import ingest_functions_to_graph
from MCP.Indexer.Utils.classes.extract_class_metadata import extract_class_metadata
from MCP.Indexer.Utils.classes.ingest_class_to_graph import ingest_classes_to_graph
from MCP.Indexer.Utils.ingest_module_to_graph import ingest_module_to_graph

logger = setup_logger(__name__)


def process_single_file(
    file_path: str, base_path: str, graph, file_dict: Dict
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Process a single Python file and ingest it into the graph.

    Args:
        file_path: Path to the Python file
        base_path: Base path for file discovery
        graph: Neo4jGraph instance
        file_dict: Dictionary mapping module names to file paths

    Returns:
        Tuple of (codebase_imports, function_metadata, class_metadata) for later relationship creation
    """
    logger.info("Starting file processing", extra={"extra_fields": {"file": file_path}})

    try:
        # Load and parse the file
        logger.debug(
            "Loading and parsing file", extra={"extra_fields": {"file": file_path}}
        )
        # Strip leading slashes/backslashes to avoid path joining issues
        clean_file_path = file_path.lstrip("/\\")
        code = load_code(Path(base_path) / clean_file_path)
        ast_code = ast.parse(code)
        file_docstring = ast.get_docstring(ast_code)

        # Build module node and get its ID
        module_id = ingest_module_to_graph(graph, file_path, code, file_docstring)

        # Extract imports
        logger.debug("Extracting imports", extra={"extra_fields": {"file": file_path}})
        imports = collect_grouped_imports(ast_code)
        codebase_imports, library_imports = classify_imports(imports, file_dict)

        # Build symbol lookups
        lookup_codebase = build_codebase_symbol_lookup(codebase_imports)
        lookup_library = build_codebase_symbol_lookup(library_imports)

        # Extract and ingest functions
        logger.debug(
            "Processing functions", extra={"extra_fields": {"file": file_path}}
        )
        function_metadata = extract_function_metadata(
            ast_code, lookup_codebase, lookup_library
        )
        ingest_functions_to_graph(function_metadata, graph, file_dict, module_id)
        log_with_context(
            logger,
            logging.INFO,
            "Functions ingested",
            file=file_path,
            function_count=len(function_metadata),
        )

        # Extract and ingest classes
        logger.debug("Processing classes", extra={"extra_fields": {"file": file_path}})
        class_metadata = extract_class_metadata(
            ast_code, lookup_codebase, lookup_library, file_path
        )
        ingest_classes_to_graph(class_metadata, graph, file_dict, module_id)
        log_with_context(
            logger,
            logging.INFO,
            "Classes ingested",
            file=file_path,
            class_count=len(class_metadata),
        )

        logger.info(
            "File processing completed successfully",
            extra={"extra_fields": {"file": file_path}},
        )

        return codebase_imports, function_metadata, class_metadata

    except Exception as e:
        logger.error(
            f"Error processing file: {str(e)}",
            extra={"extra_fields": {"file": file_path}},
            exc_info=True,
        )
        raise
