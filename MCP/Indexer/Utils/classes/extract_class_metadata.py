import ast
from typing import Dict, Set

from logger import setup_logger
from MCP.Indexer.Utils.common import classify_symbol, extract_dotted_name_from_node
from MCP.Indexer.Utils.functions.function_metadata import extract_function_metadata

logger = setup_logger(__name__)


def extract_method_metadata_from_body(body, lookup_codebase, lookup_library):
    """Run your function extractor on function nodes inside a class body."""
    fake_module = ast.Module(body=body, type_ignores=[])
    return extract_function_metadata(fake_module, lookup_codebase, lookup_library)


def get_base_name(node: ast.expr) -> str:
    """
    Extract the base class name from an AST node.
    
    Args:
        node: AST node representing a base class
    
    Returns:
        The base class name or None
    """
    return extract_dotted_name_from_node(node)


def _collect_local_classes(tree):
    """Collect all class names defined in the file."""
    local_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            local_classes.add(node.name)
    return local_classes


def _create_class_info_structure(node):
    """Create the base structure for class metadata."""
    return {
        "name": node.name,
        "docstring": ast.get_docstring(node),
        "start_line": node.lineno,
        "end_line": getattr(node, "end_lineno", None),
        "decorators": [],
        "base_classes": [],
        "attributes": [],
        "methods": [],
    }


def _extract_decorators(
    node: ast.ClassDef, lookup_codebase: Dict[str, str], lookup_library: Dict[str, str]
) -> list:
    """
    Extract decorator information from a class node.
    
    Args:
        node: Class node
        lookup_codebase: Codebase symbol lookup
        lookup_library: Library symbol lookup
    
    Returns:
        List of decorator information dictionaries
    """
    decorators = []

    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            name = dec.id
        elif isinstance(dec, ast.Attribute):
            name = dec.attr
        else:
            continue

        group, fq = classify_symbol(name, lookup_codebase, lookup_library)

        if fq:
            decorators.append(
                {
                    "name": name,
                    "scope": group,
                    "importing_from": fq,
                }
            )

    return decorators


def _extract_base_classes(
    node: ast.ClassDef, local_classes: Set[str], lookup: Dict[str, str], current_file: str
) -> list:
    """
    Extract base class information from a class node.
    
    Args:
        node: Class node
        local_classes: Set of class names defined in the current file
        lookup: Combined codebase and library symbol lookup
        current_file: Current file path
    
    Returns:
        List of base class information dictionaries
    """
    base_classes = []

    for base in node.bases:
        base_name = get_base_name(base)

        if not base_name:
            continue

        # Check if base class is defined in the same file
        if base_name in local_classes:
            importing_from = current_file  # local class
        else:
            # Otherwise check the lookup (imported or external)
            importing_from = lookup.get(base_name)

        base_classes.append(
            {
                "name": base_name,
                "importing_from": importing_from,
            }
        )

    return base_classes


def _extract_class_attributes(node: ast.ClassDef) -> list:
    """
    Extract class-level attributes from a class node.
    
    Args:
        node: Class node
    
    Returns:
        List of attribute information dictionaries
    """
    attributes = []

    for item in node.body:
        if isinstance(item, ast.Assign):
            # Handle: name = value
            for target in item.targets:
                if isinstance(target, ast.Name):
                    attr_name = target.id
                    attr_value = ast.unparse(item.value)

                    attributes.append(
                        {
                            "name": attr_name,
                            "value": attr_value,
                            "lineno": item.lineno,
                        }
                    )

        elif isinstance(item, ast.AnnAssign):
            # Handle: name: Type = value (annotated assignment)
            if isinstance(item.target, ast.Name):
                attr_name = item.target.id
                attr_type = ast.unparse(item.annotation) if item.annotation else None
                attr_value = ast.unparse(item.value) if item.value else None

                attributes.append(
                    {
                        "name": attr_name,
                        "annotation": attr_type,
                        "value": attr_value,
                        "lineno": item.lineno,
                    }
                )

    return attributes


def _process_single_class(
    node: ast.ClassDef,
    lookup_codebase: Dict[str, str],
    lookup_library: Dict[str, str],
    local_classes: Set[str],
    current_file: str,
) -> Dict:
    """
    Process a single ClassDef node and extract all its metadata.
    
    Args:
        node: Class definition node
        lookup_codebase: Codebase symbol lookup
        lookup_library: Library symbol lookup
        local_classes: Set of classes defined in current file
        current_file: Current file path
    
    Returns:
        Dictionary containing class metadata
    """
    lookup = lookup_codebase | lookup_library

    class_info = _create_class_info_structure(node)

    # Extract decorators
    class_info["decorators"] = _extract_decorators(
        node, lookup_codebase, lookup_library
    )

    # Extract base classes
    class_info["base_classes"] = _extract_base_classes(
        node, local_classes, lookup, current_file
    )

    # Extract class attributes
    class_info["attributes"] = _extract_class_attributes(node)

    # Extract methods
    class_info["methods"] = extract_method_metadata_from_body(
        node.body,
        lookup_codebase,
        lookup_library,
    )

    return class_info


def extract_class_metadata(
    tree: ast.Module, lookup_codebase: Dict[str, str], lookup_library: Dict[str, str], current_file: str
) -> list:
    """
    Extract metadata for all classes in the AST tree.
    
    Args:
        tree: AST module node
        lookup_codebase: Codebase symbol lookup
        lookup_library: Library symbol lookup
        current_file: Current file path
    
    Returns:
        List of class metadata dictionaries
    """
    logger.debug("Starting class metadata extraction")

    # First pass: collect ALL classes in the file (including nested ones)
    local_classes = _collect_local_classes(tree)
    logger.debug(
        "Local classes collected",
        extra={"extra_fields": {"local_class_count": len(local_classes)}},
    )

    classes = []

    # Walk entire tree to find all ClassDef nodes
    for node in ast.walk(tree):
        # Only process ClassDef nodes
        if not isinstance(node, ast.ClassDef):
            continue

        try:
            class_info = _process_single_class(
                node, lookup_codebase, lookup_library, local_classes, current_file
            )
            classes.append(class_info)

            logger.debug(
                "Class metadata extracted",
                extra={
                    "extra_fields": {
                        "class": node.name,
                        "method_count": len(class_info.get("methods", [])),
                        "base_count": len(class_info.get("base_classes", [])),
                    }
                },
            )

        except Exception as e:
            logger.warning(
                f"Failed to extract metadata for class: {str(e)}",
                extra={"extra_fields": {"class": getattr(node, "name", "unknown")}},
            )
            continue

    logger.info(
        "Class metadata extraction completed",
        extra={"extra_fields": {"total_classes": len(classes)}},
    )
    return classes
