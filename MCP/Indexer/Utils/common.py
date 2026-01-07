"""
Common utilities for symbol classification and AST operations.
Consolidates duplicate logic following DRY principle.
"""
import ast
from typing import Tuple, Optional, Dict, Any

from logger import setup_logger

logger = setup_logger(__name__)


def classify_symbol(
    name: str, codebase_lookup: Dict[str, str], library_lookup: Dict[str, str]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Classify a symbol as either codebase or library symbol.
    
    Args:
        name: The symbol name to classify
        codebase_lookup: Dictionary mapping local names to codebase fully-qualified names
        library_lookup: Dictionary mapping local names to library fully-qualified names
    
    Returns:
        Tuple of (group_name, fully_qualified_name) or (None, None) if not found
    """
    if name in codebase_lookup:
        return "codebase", codebase_lookup[name]

    if name in library_lookup:
        return "library", library_lookup[name]

    return None, None


def extract_name_from_ast_node(node: ast.expr) -> Optional[str]:
    """
    Extract a name from an AST node (handles Name and Attribute nodes).
    
    Args:
        node: AST node to extract name from
    
    Returns:
        The extracted name or None
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    return None


def extract_dotted_name_from_node(node: ast.expr) -> Optional[str]:
    """
    Extract a fully dotted name from an AST node.
    E.g., ast.Attribute node for 'a.b.c' returns 'a.b.c'.
    
    Args:
        node: AST node to extract dotted name from
    
    Returns:
        The dotted name or None
    """
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        parts.reverse()
        return ".".join(parts)

    return None


def collect_ast_walk_symbols(
    node: ast.AST, codebase_lookup: Dict[str, str], library_lookup: Dict[str, str]
) -> Dict[str, list]:
    """
    Walk AST node and collect all symbols classified as codebase/library.
    
    Args:
        node: AST node to walk through
        codebase_lookup: Dictionary of codebase symbols
        library_lookup: Dictionary of library symbols
    
    Returns:
        Dictionary with 'codebase' and 'library' keys containing sorted unique symbols
    """
    used_codebase = set()
    used_library = set()

    for inner in ast.walk(node):
        symbol = extract_name_from_ast_node(inner)
        if not symbol:
            continue

        group, fq = classify_symbol(symbol, codebase_lookup, library_lookup)
        if not fq:
            continue

        if group == "codebase":
            used_codebase.add(fq)
        elif group == "library":
            used_library.add(fq)

    return {
        "codebase": sorted(used_codebase),
        "library": sorted(used_library),
    }
