import ast
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import setup_logger
from common import classify_symbol, collect_ast_walk_symbols, extract_name_from_ast_node

logger = setup_logger(__name__)


def extract_arg_annotation(arg: ast.arg, codebase_lookup: Dict) -> Dict[str, str]:
    """
    Extract annotation display string from function argument.
    
    Args:
        arg: Function argument node
        codebase_lookup: Dictionary of codebase symbols for resolving types
    
    Returns:
        Dictionary with annotation_display key
    """
    if not arg.annotation:
        return {"annotation_display": None}

    return {"annotation_display": ast.unparse(arg.annotation)}


def _create_function_info_structure(node, parent_function=None):
    """Create the base structure for function metadata."""
    func_info = {
        "name": node.name,
        "docstring": ast.get_docstring(node),
        "start_line": node.lineno,
        "end_line": getattr(node, "end_lineno", None),
        "args": [],
        "decorators": [],
        "calls": {
            "codebase": [],
            "library": [],
        },
        "depends": [],
    }

    if parent_function:
        func_info["parent_function"] = parent_function

    return func_info


def _extract_function_arguments(node, codebase_lookup):
    """Extract all arguments from a function node."""
    args = []

    # Regular and keyword-only arguments
    for arg in node.args.args + node.args.kwonlyargs:
        args.append({"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)})

    # *args
    if node.args.vararg:
        args.append(
            {
                "name": "*" + node.args.vararg.arg,
                **extract_arg_annotation(node.args.vararg, codebase_lookup),
            }
        )

    # **kwargs
    if node.args.kwarg:
        args.append(
            {
                "name": "**" + node.args.kwarg.arg,
                **extract_arg_annotation(node.args.kwarg, codebase_lookup),
            }
        )

    return args


def _extract_decorators(node: ast.AST, codebase_lookup: Dict[str, str], library_lookup: Dict[str, str]) -> list:
    """
    Extract decorator information from a function node.
    
    Args:
        node: Function node
        codebase_lookup: Codebase symbol lookup
        library_lookup: Library symbol lookup
    
    Returns:
        List of decorator information dictionaries
    """
    decorators = []

    for dec in node.decorator_list:
        name = extract_name_from_ast_node(dec)
        if not name:
            continue

        group, fq = classify_symbol(name, codebase_lookup, library_lookup)

        if fq:
            decorators.append(
                {
                    "name": name,
                    "scope": group,
                    "importing_from": fq,
                }
            )

    return decorators


def _extract_function_calls(
    node: ast.AST, codebase_lookup: Dict[str, str], library_lookup: Dict[str, str]
) -> Dict[str, list]:
    """
    Extract all function/symbol calls from the function body.
    
    Args:
        node: Function node
        codebase_lookup: Codebase symbol lookup
        library_lookup: Library symbol lookup
    
    Returns:
        Dictionary with 'codebase' and 'library' keys containing called symbols
    """
    return collect_ast_walk_symbols(node, codebase_lookup, library_lookup)


def extract_nested_functions(node, codebase_lookup, library_lookup, parent_name):
    """
    Extract metadata for functions defined inside another function.
    """
    nested_functions = []

    for inner in node.body:
        if not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Create function info structure
        fn = _create_function_info_structure(inner, parent_function=parent_name)

        # Extract arguments (nested functions don't have vararg/kwarg typically, but handle them)
        for arg in inner.args.args + inner.args.kwonlyargs:
            fn["args"].append(
                {"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)}
            )

        # Extract decorators
        fn["decorators"] = _extract_decorators(inner, codebase_lookup, library_lookup)

        # Extract function calls
        fn["calls"] = _extract_function_calls(inner, codebase_lookup, library_lookup)

        # Recurse for deeper nested functions
        new_parent_path = f"{parent_name}/{inner.name}" if parent_name else inner.name

        deeper = extract_nested_functions(
            inner,
            codebase_lookup,
            library_lookup,
            parent_name=new_parent_path,
        )

        fn["depends"] = [d["name"] for d in deeper]

        nested_functions.append(fn)
        nested_functions.extend(deeper)

    return nested_functions


def extract_function_metadata(tree, codebase_lookup, library_lookup):
    """Extract metadata for all top-level functions in the AST tree."""
    logger.debug("Starting function metadata extraction")
    functions = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        try:
            # Create function info structure
            func_info = _create_function_info_structure(node)

            # Extract arguments
            func_info["args"] = _extract_function_arguments(node, codebase_lookup)

            # Extract decorators
            func_info["decorators"] = _extract_decorators(
                node, codebase_lookup, library_lookup
            )

            # Extract function calls
            func_info["calls"] = _extract_function_calls(
                node, codebase_lookup, library_lookup
            )

            # Extract nested functions
            nested = extract_nested_functions(
                node,
                codebase_lookup,
                library_lookup,
                parent_name=node.name,
            )

            func_info["depends"] = [f["name"] for f in nested]

            functions.append(func_info)
            functions.extend(nested)

            logger.debug(
                "Function metadata extracted",
                extra={
                    "extra_fields": {"function": node.name, "nested_count": len(nested)}
                },
            )

        except Exception as e:
            logger.warning(
                f"Failed to extract metadata for function: {str(e)}",
                extra={"extra_fields": {"function": getattr(node, "name", "unknown")}},
            )
            continue

    logger.info(
        "Function metadata extraction completed",
        extra={"extra_fields": {"total_functions": len(functions)}},
    )
    return functions
