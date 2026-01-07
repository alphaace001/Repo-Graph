"""
Main entry point for Knowledge Graph API server.
"""
import uvicorn
from config import API_PORT, API_HOST


def main():
    """Start the FastAPI backend server."""
    print(f"Starting Knowledge Graph API server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "API.main:app",  # Use string import for proper package resolution
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
