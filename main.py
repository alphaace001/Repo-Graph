import sys
from pathlib import Path

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent / "API"))


def main():
    """Start the FastAPI backend server from API/main.py"""
    import uvicorn
    from API.main import app
    from config import API_PORT, API_HOST
    
    print(f"Starting Knowledge Graph API server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
