import ast
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from utils import discover_py_files, load_code, convert_file_paths_to_modules
from import_utils import collect_grouped_imports, classify_imports
from functions.function_utils import build_codebase_symbol_lookup
from functions.function_metadata import extract_function_metadata
from functions.ingest_function_to_graph import ingest_functions_to_graph
from classes.extract_class_metadata import extract_class_metadata
from classes.ingest_class_to_graph import ingest_classes_to_graph
from cypherquery_utils import create_import_relationships
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import setup_logger, LogContext, log_with_context

from langchain_neo4j import Neo4jGraph

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger(__name__)

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URL"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
)

path = "D:\\KGassign\\fastapi"
files = discover_py_files(path)
file_dict = convert_file_paths_to_modules(files)

# Save file_dict for reference
with open("file_dict.json", "w", encoding="utf-8") as f:
    json.dump(file_dict, f, indent=2, ensure_ascii=False)
logger.info("File dictionary saved to file_dict.json")


def build_module_node(
    graph: Neo4jGraph, current_file: str, code: str, module_docstring: str
):
    """Build a Module node and return its element ID."""
    logger.debug("Building module node", extra={"extra_fields": {"file": current_file}})

    module_name = current_file
    content = code

    try:
        # First, create/merge the module without docstring condition
        result = graph.query(
            """
            MERGE (m:Module {name: $name})
            SET m.content = $content
            RETURN elementId(m) as module_id
            """,
            {
                "name": module_name,
                "content": content,
            },
        )

        if not result or len(result) == 0:
            raise ValueError(f"Failed to create module node for {current_file}")

        module_id = result[0]["module_id"]

        # Then, create docstring relationship if docstring exists
        if module_docstring and module_docstring.strip():
            doc_name = f"{module_name}_docstring"
            graph.query(
                """
                MATCH (m:Module)
                WHERE elementId(m) = $module_id
                
                MERGE (d:Docstring {name: $doc_name})
                SET d.content = $doc_text
                
                MERGE (m)-[:DOCUMENTED_BY]->(d)
                """,
                {
                    "module_id": module_id,
                    "doc_name": doc_name,
                    "doc_text": module_docstring,
                },
            )

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


def class_to_class_relationships(graph, class_metadata, file_dict, source_file_path):
    """
    Process class metadata to create:
    1. INHERITS_FROM relationships for base classes
    2. Call function_to_function_relationships for class methods

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
            # e.g., "pydantic.BaseModel" -> module="pydantic", symbol="BaseModel"
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
            function_to_function_relationships(
                graph, methods, file_dict, source_file_path
            )


def function_to_function_relationships(
    graph, function_metadata, file_dict, source_file_path
):
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

        # creating a relationship for calls
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


def process_single_file(
    file_path: str, base_path: str, graph: Neo4jGraph, file_dict: dict
) -> tuple[list[dict], list[dict], list[dict]]:
    """Process a single Python file and ingest it into the graph.

    Returns:
        Tuple of (codebase_imports, function_metadata, class_metadata) for later relationship creation
    """
    logger.info("Starting file processing", extra={"extra_fields": {"file": file_path}})

    try:
        # Load and parse the file
        logger.debug(
            "Loading and parsing file", extra={"extra_fields": {"file": file_path}}
        )
        code = load_code(Path(base_path) / file_path)
        ast_code = ast.parse(code)
        file_docstring = ast.get_docstring(ast_code)

        # Build module node and get its ID
        module_id = build_module_node(graph, file_path, code, file_docstring)

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


def ingest_all_files():
    """Ingest all Python files from the codebase into the graph."""
    with LogContext(logger=logger) as correlation_id:
        logger.info(
            "Starting batch file ingestion",
            extra={"extra_fields": {"total_files": len(files), "path": path}},
        )

        success_count = 0
        error_count = 0
        errors = []
        all_imports = {}  # Store imports for each file
        all_functions = {}  # Store function metadata for each file
        all_classes = {}  # Store class metadata for each file

        for idx, file_path in enumerate(files, 1):
            with LogContext(logger=logger):  # New correlation ID for each file
                try:
                    codebase_imports, function_metadata, class_metadata = (
                        process_single_file(file_path, path, graph, file_dict)
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

        # Write collected data to JSON files
        logger.info("Writing metadata to files")
        try:
            with open("codebase_imports.json", "w", encoding="utf-8") as f:
                json.dump(all_imports, f, indent=2, ensure_ascii=False)
            logger.info("Codebase imports written to codebase_imports.json")
        except Exception as e:
            logger.error(f"Failed to write codebase imports: {str(e)}", exc_info=True)

        try:
            with open("function_metadata.json", "w", encoding="utf-8") as f:
                json.dump(all_functions, f, indent=2, ensure_ascii=False)
            logger.info("Function metadata written to function_metadata.json")
        except Exception as e:
            logger.error(f"Failed to write function metadata: {str(e)}", exc_info=True)

        try:
            with open("class_metadata.json", "w", encoding="utf-8") as f:
                json.dump(all_classes, f, indent=2, ensure_ascii=False)
            logger.info("Class metadata written to class_metadata.json")
        except Exception as e:
            logger.error(f"Failed to write class metadata: {str(e)}", exc_info=True)

        # Create import relationships after all modules are created
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

        # Create function-to-function relationships after all modules are created
        logger.info(
            "Creating function-to-function relationships",
            extra={"extra_fields": {"total_files": len(all_functions)}},
        )
        for file_path, function_metadata in all_functions.items():
            try:
                function_to_function_relationships(
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

        # Create class-to-class relationships (inheritance) and process method calls
        logger.info(
            "Creating class-to-class relationships",
            extra={"extra_fields": {"total_files": len(all_classes)}},
        )
        for file_path, class_metadata in all_classes.items():
            try:
                class_to_class_relationships(
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

# all_functions = json.load(open("function_metadata.json", "r", encoding="utf-8"))
# file_dict = json.load(open("file_dict.json", "r", encoding="utf-8"))
# for file_path, function_metadata in all_functions.items():
#     try:
#         function_to_function_relationships(
#             graph, function_metadata, file_dict, file_path
#         )
#         logger.debug(
#             "Function relationships created",
#             extra={
#                 "extra_fields": {
#                     "file": file_path,
#                     "function_count": len(function_metadata),
#                 }
#             },
#         )
#     except Exception as e:
#         logger.error(
#             f"Failed to create function relationships: {str(e)}",
#             extra={"extra_fields": {"file": file_path}},
#             exc_info=True,
#         )
