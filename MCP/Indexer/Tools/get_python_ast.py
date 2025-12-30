import ast
from pathlib import Path


def parse_python_file(file_path: str, base_path: str) -> ast.AST:
    """
    Parse a Python file and return its AST.

    Args:
        file_path (str): The path to the Python file.
    Returns:
        ast.AST: The abstract syntax tree of the parsed Python file.
    """
    # Strip leading slashes/backslashes to avoid path joining issues
    file_path = file_path.lstrip("/\\")
    full_path = Path(base_path) / file_path
    with open(full_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    ast_code = ast.parse(file_content)
    return ast.dump(ast_code, indent=2)
