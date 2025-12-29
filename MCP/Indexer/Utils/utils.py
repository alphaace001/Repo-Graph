import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import setup_logger

logger = setup_logger(__name__)

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
    """Discover all Python files in the given directory."""
    logger.debug("Starting file discovery", extra={'extra_fields': {'root': root}})
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

    logger.info("File discovery completed", 
               extra={'extra_fields': {'file_count': len(results), 'root': root}})
    return results


def load_code(path: Path) -> str:
    """Load Python source code from a file."""
    try:
        path = Path(path)
        if path.is_dir():
            path = path / "__init__.py"
        
        logger.debug("Loading code", extra={'extra_fields': {'path': str(path)}})
        code = path.read_text(encoding="utf-8")
        logger.debug("Code loaded successfully", 
                    extra={'extra_fields': {'path': str(path), 'size': len(code)}})
        return code
        
    except Exception as e:
        logger.error(f"Failed to load code: {str(e)}", 
                    extra={'extra_fields': {'path': str(path)}}, 
                    exc_info=True)
        raise


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
