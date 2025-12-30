import sys
import json
from pathlib import Path

# Setup Python paths
indexer_path = Path(__file__).parent.parent  # Go up to Indexer directory
sys.path.insert(0, str(indexer_path.parent.parent))  # Add KG-Assignment to path
sys.path.insert(0, str(indexer_path))  # Add Indexer to path
sys.path.insert(0, str(indexer_path / "Tools"))  # Add Tools to path
sys.path.insert(0, str(indexer_path / "Utils"))  # Add Utils to path

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BASE_PATH = os.getenv("BASE_PATH", "D:\\KGassign\\fastapi")

# Import the underlying function
from Tools.get_python_ast import parse_python_file

# Test the function
file_path = "\\fastapi\\routing.py"
# Strip leading slashes/backslashes to avoid path issues
file_path_clean = file_path.lstrip("/\\")

print(f"Testing parse_python_file with file_path: {file_path}")
print(f"Cleaned file_path: {file_path_clean}")
print(f"Base path: {BASE_PATH}")
print("-" * 80)

try:
    ast_tree = parse_python_file(file_path_clean, BASE_PATH)

    print("Result (AST Dump):")
    print(ast_tree[:500])  # Print first 500 characters
    print("\n... (truncated)")
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
