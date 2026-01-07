"""
Neo4j graph connection for Analyst MCP server.
Standalone implementation for containerized deployment.
"""

import os
from typing import List, Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv

from logger import get_mcp_safe_logger

logger = get_mcp_safe_logger(__name__)

# Load environment variables
load_dotenv()


class Neo4jGraph:
    """Simplified Neo4j graph connection."""

    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j URI (defaults to env var NEO4J_URI or NEO4J_URL)
            username: Neo4j username (defaults to env var NEO4J_USERNAME)
            password: Neo4j password (defaults to env var NEO4J_PASSWORD)
        """
        self.uri = (
            uri
            or os.getenv("NEO4J_URI")
            or os.getenv("NEO4J_URL", "bolt://localhost:7687")
        )
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")

        logger.info(f"Connecting to Neo4j at {self.uri}")
        self.driver = GraphDatabase.driver(
            self.uri, auth=(self.username, self.password)
        )

        # Verify connection
        try:
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def query(
        self, query: str, parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result dictionaries
        """
        if parameters is None:
            parameters = {}

        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __del__(self):
        """Ensure connection is closed on deletion."""
        self.close()


# Create a singleton instance
graph = Neo4jGraph()
