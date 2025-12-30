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
from Tools.process_single_file import ingest_single_file

# Test the function
file_path = "\\fastapi\\routing.py"
# Strip leading slashes/backslashes to avoid path issues
file_path_clean = file_path.lstrip("/\\")

print(f"Testing ingest_single_file with file_path: {file_path}")
print(f"Cleaned file_path: {file_path_clean}")
print(f"Base path: {BASE_PATH}")
print("-" * 80)

result = ingest_single_file(file_path_clean, BASE_PATH)

print("Result:")
print(json.dumps(result, indent=2))
