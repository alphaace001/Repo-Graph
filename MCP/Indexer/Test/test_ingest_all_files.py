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
from Tools.index_repo import ingest_all_files

# Test the function
path = "\\fastapi"  # Subdirectory within BASE_PATH
path_clean = path.lstrip("/\\")

# Construct full path: BASE_PATH + path
if path_clean:
    full_path = str(Path(BASE_PATH) / path_clean)
else:
    full_path = BASE_PATH

print(f"Testing ingest_all_files with path: {path}")
print(f"Cleaned path: {path_clean}")
print(f"Full path: {full_path}")
print("-" * 80)

try:
    result = ingest_all_files(full_path)
    print("Result:")
    print(result)
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
