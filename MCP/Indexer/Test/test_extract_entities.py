import sys
import json
import ast
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
from Tools.extract_entities import extract_entities

# Test the function
file_path = "\\fastapi\\routing.py"
# Strip leading slashes/backslashes to avoid path issues
file_path_clean = file_path.lstrip("/\\")
full_path = str(Path(BASE_PATH) / file_path_clean)

print(f"Testing extract_entities with file_path: {file_path}")
print(f"Cleaned file_path: {file_path_clean}")
print(f"Full path: {full_path}")
print("-" * 80)

try:
    # Read and parse the file to get AST
    with open(full_path, "r", encoding="utf-8") as f:
        code_content = f.read()
    ast_code = ast.parse(code_content)

    # Call extract_entities
    result = extract_entities(ast_code, None, file_path)

    print("Result:")
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
