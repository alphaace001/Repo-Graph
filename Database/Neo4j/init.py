"""
Initialize Neo4j graph connection and environment variables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger(__name__)

# Initialize Neo4j graph connection
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URL"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
)

logger.info("Knowledge graph initialized successfully")
