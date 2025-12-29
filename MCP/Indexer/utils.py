from pathlib import Path

SKIP_DIRS = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "site-packages",
    "dist-packages",
    "tests",
    "test",
    "__tests__",
    "docs",
    "docs_src",
}


def discover_py_files(root: str):
    root = Path(root).resolve()

    results = []

    for path in root.rglob("*.py"):

        parts = set(path.parts)

        # skip unwanted directories
        if parts & SKIP_DIRS:
            continue

        # skip test files
        name = path.name.lower()
        if name.startswith("test_") or name.endswith("_test.py"):
            continue

        # relative path -> POSIX string
        rel = path.relative_to(root).as_posix()

        # --- new logic: normalize __init__.py ---
        if rel.endswith("/__init__.py"):
            rel = rel.rsplit("/__init__.py", 1)[0]

        results.append(rel)

    return results


def load_code(path: Path) -> str:
    path = Path(path)
    if path.is_dir():
        path = path / "__init__.py"
    return path.read_text(encoding="utf-8")


def convert_file_paths_to_modules(file_paths: list[str]) -> dict:
    """
    Convert file paths to module names.

    Args:
        file_paths: List of file path strings (e.g., ["fastapi/utils.py", "fastapi/routing.py"])

    Returns:
        Dictionary mapping module names to original file paths
    """
    modules = {}

    for file_path in file_paths:
        original_path = file_path

        # Remove .py extension
        if file_path.endswith(".py"):
            file_path = file_path[:-3]

        # Replace / with .
        module_name = file_path.replace("/", ".")

        # Handle __init__ modules (e.g., "fastapi.security.__init__" -> "fastapi.security")
        if module_name.endswith(".__init__"):
            module_name = module_name.rsplit(".__init__", 1)[0]

        modules[module_name] = original_path

    return modules
