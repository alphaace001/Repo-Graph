import ast
import sys
from pathlib import Path
from typing import Dict, List

# Add KG-Assignment to path for logger and other modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add Utils directory for common and other shared modules
sys.path.insert(0, str(Path(__file__).parent / "Utils"))
# Add current Indexer directory for relative Utils imports
sys.path.insert(0, str(Path(__file__).parent))

from Utils.functions.function_metadata import extract_function_metadata
from Utils.classes.extract_class_metadata import extract_class_metadata
from Utils.functions.function_utils import build_codebase_symbol_lookup
from Utils.import_utils import collect_grouped_imports, classify_imports
from Utils.utils import load_code


def _extract_arguments_from_metadata(func_meta: dict) -> List[Dict]:
    """Extract arguments from function metadata."""
    arguments = []
    if "args" in func_meta and func_meta["args"]:
        for arg in func_meta["args"]:
            arguments.append({
                "id": f"{func_meta.get('name', 'unknown')}_arg_{arg.get('name', 'unknown')}",
                "name": arg.get("name"),
                "annotation": arg.get("annotation_display"),
                "default": arg.get("default"),
                "parent_function": func_meta.get("name"),
            })
    return arguments


def _extract_methods_from_class(class_meta: dict) -> List[Dict]:
    """Extract methods from class metadata."""
    methods = []
    if "methods" in class_meta and class_meta["methods"]:
        for method in class_meta["methods"]:
            methods.append({
                "id": f"{class_meta.get('name', 'unknown')}.{method.get('name', 'unknown')}",
                "name": method.get("name"),
                "docstring": method.get("docstring"),
                "start_line": method.get("start_line"),
                "end_line": method.get("end_line"),
                "decorators": method.get("decorators", []),
                "args": method.get("args", []),
                "parent_class": class_meta.get("name"),
                "calls": method.get("calls", {}),
            })
    return methods


def _build_relationships(function_metadata: List[Dict], class_metadata: List[Dict]) -> List[Dict]:
    """Build relationships between entities."""
    relationships = []

    # 1. Class inheritance relationships
    for class_meta in class_metadata:
        class_name = class_meta.get("name")
        base_classes = class_meta.get("bases", [])
        for base_class in base_classes:
            relationships.append({
                "source": class_name,
                "target": base_class,
                "type": "inherits_from",
                "source_type": "class",
                "target_type": "class",
            })

    # 2. Class contains methods relationships
    for class_meta in class_metadata:
        class_name = class_meta.get("name")
        methods = class_meta.get("methods", [])
        for method in methods:
            method_name = method.get("name")
            relationships.append({
                "source": class_name,
                "target": f"{class_name}.{method_name}",
                "type": "contains",
                "source_type": "class",
                "target_type": "method",
            })

    # 3. Function/Method depends on other functions/methods
    all_functions = function_metadata.copy()
    
    # Add methods to the pool of functions
    for class_meta in class_metadata:
        for method in class_meta.get("methods", []):
            all_functions.append({
                "name": f"{class_meta.get('name')}.{method.get('name')}",
                "calls": method.get("calls", {}),
            })

    # Build dependency relationships
    for func in all_functions:
        func_name = func.get("name")
        calls = func.get("calls", {})
        
        # Handle codebase and library calls
        for call_type in ["codebase", "library"]:
            if call_type in calls:
                for called_func in calls[call_type]:
                    relationships.append({
                        "source": func_name,
                        "target": called_func,
                        "type": "depends_on",
                        "source_type": "function" if "." not in func_name else "method",
                        "target_type": "function" if "." not in called_func else "method",
                        "call_category": call_type,
                    })

    # 4. Function/Method documented by docstring
    for func in function_metadata:
        func_name = func.get("name")
        docstring = func.get("docstring")
        if docstring:
            relationships.append({
                "source": func_name,
                "target": f"{func_name}_docstring",
                "type": "documented_by",
                "source_type": "function",
                "target_type": "docstring",
            })

    for class_meta in class_metadata:
        class_name = class_meta.get("name")
        docstring = class_meta.get("docstring")
        if docstring:
            relationships.append({
                "source": class_name,
                "target": f"{class_name}_docstring",
                "type": "documented_by",
                "source_type": "class",
                "target_type": "docstring",
            })
        
        for method in class_meta.get("methods", []):
            method_name = f"{class_name}.{method.get('name')}"
            docstring = method.get("docstring")
            if docstring:
                relationships.append({
                    "source": method_name,
                    "target": f"{method_name}_docstring",
                    "type": "documented_by",
                    "source_type": "method",
                    "target_type": "docstring",
                })

    # 5. Function/Method parameters relationships
    for func in function_metadata:
        func_name = func.get("name")
        args = func.get("args", [])
        for arg in args:
            arg_name = arg.get("name")
            relationships.append({
                "source": func_name,
                "target": f"{func_name}_param_{arg_name}",
                "type": "parameters",
                "source_type": "function",
                "target_type": "argument",
                "parameter_name": arg_name,
            })

    for class_meta in class_metadata:
        class_name = class_meta.get("name")
        for method in class_meta.get("methods", []):
            method_name = f"{class_name}.{method.get('name')}"
            args = method.get("args", [])
            for arg in args:
                arg_name = arg.get("name")
                relationships.append({
                    "source": method_name,
                    "target": f"{method_name}_param_{arg_name}",
                    "type": "parameters",
                    "source_type": "method",
                    "target_type": "argument",
                    "parameter_name": arg_name,
                })

    return relationships


def extract_entities(
    ast_code: ast.AST, file_dict: Dict = None, current_file: str = None
) -> dict:
    """
    Extract entities and relationships from the given AST.

    This function extracts all code entities (functions, classes, methods, arguments, docstrings)
    and builds relationships between them for knowledge graph construction.

    Args:
        ast_code: The AST of the Python code.
        file_dict: Optional dictionary mapping module names to file paths.
                   Used for import classification. Defaults to empty dict.
        current_file: Optional file path for class metadata extraction context.

    Returns:
        A dictionary containing:
        {
            "entities": {
                "file_docstring": str or None,
                "codebase_imports": list,
                "library_imports": list,
                "functions": list,
                "classes": list,
                "methods": list,
                "arguments": list,
                "docstrings": list,
            },
            "relationships": [
                {
                    "source": str,
                    "target": str,
                    "type": str,  # inherits_from, contains, depends_on, documented_by, parameters
                    "source_type": str,
                    "target_type": str,
                    ...additional metadata...
                }
            ]
        }
    """
    # Default to empty dict if not provided
    if file_dict is None:
        file_dict = {}

    # Extract file-level docstring
    file_docstring = ast.get_docstring(ast_code)

    # Extract and classify imports
    imports = collect_grouped_imports(ast_code)
    codebase_imports, library_imports = classify_imports(imports, file_dict)

    # Build symbol lookups for both codebase and library imports
    lookup_codebase = build_codebase_symbol_lookup(codebase_imports)
    lookup_library = build_codebase_symbol_lookup(library_imports)

    # Extract function metadata with proper lookups
    function_metadata = extract_function_metadata(
        ast_code, lookup_codebase, lookup_library
    )

    # Extract class metadata with proper lookups and file context
    class_metadata = extract_class_metadata(
        ast_code, lookup_codebase, lookup_library, current_file or ""
    )

    # Extract all arguments from functions
    all_arguments = []
    for func in function_metadata:
        all_arguments.extend(_extract_arguments_from_metadata(func))

    # Extract all methods from classes
    all_methods = []
    for class_meta in class_metadata:
        all_methods.extend(_extract_methods_from_class(class_meta))
        # Add arguments from methods
        for method in class_meta.get("methods", []):
            all_arguments.extend(_extract_arguments_from_metadata(method))

    # Extract all docstrings
    all_docstrings = []
    
    if file_docstring:
        all_docstrings.append({
            "id": "file_docstring",
            "content": file_docstring,
            "entity_type": "file",
        })
    
    for func in function_metadata:
        if func.get("docstring"):
            all_docstrings.append({
                "id": f"{func.get('name')}_docstring",
                "content": func.get("docstring"),
                "entity_type": "function",
                "parent": func.get("name"),
            })

    for class_meta in class_metadata:
        if class_meta.get("docstring"):
            all_docstrings.append({
                "id": f"{class_meta.get('name')}_docstring",
                "content": class_meta.get("docstring"),
                "entity_type": "class",
                "parent": class_meta.get("name"),
            })
        
        for method in class_meta.get("methods", []):
            if method.get("docstring"):
                all_docstrings.append({
                    "id": f"{class_meta.get('name')}.{method.get('name')}_docstring",
                    "content": method.get("docstring"),
                    "entity_type": "method",
                    "parent": f"{class_meta.get('name')}.{method.get('name')}",
                })

    # Build relationships
    relationships = _build_relationships(function_metadata, class_metadata)

    return {
        "entities": {
            "file_docstring": file_docstring,
            "codebase_imports": codebase_imports,
            "library_imports": library_imports,
            "functions": function_metadata,
            "classes": class_metadata,
            "methods": all_methods,
            "arguments": all_arguments,
            "docstrings": all_docstrings,
        },
        "relationships": relationships,
    }


if __name__ == "__main__":
    BASE_PATH = "D:\\KGassign\\fastapi"
    code = load_code(f"{BASE_PATH}\\fastapi\\routing.py")
    ast_code = ast.parse(code)
    result = extract_entities(ast_code, current_file="fastapi/routing.py")
    print(result)
