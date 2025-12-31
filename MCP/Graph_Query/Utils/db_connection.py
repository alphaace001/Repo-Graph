"""
Neo4j database connection management for Graph Query MCP.
Uses the shared Neo4j connection from Database.Neo4j module.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import get_mcp_safe_logger

# Import the shared graph instance from Database.Neo4j
# Import the shared graph instance from Database.Neo4j
from Database.Neo4j import graph

logger = get_mcp_safe_logger(__name__)


class Neo4jConnection:
    """
    Wrapper for Neo4j database connections.
    Uses the shared graph instance from Database.Neo4j module.
    """

    _instance: Optional["Neo4jConnection"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Neo4j connection wrapper (singleton pattern)."""
        self.graph = graph
        logger.info("Neo4jConnection initialized with shared graph instance")

    def execute_query(self, query: str, parameters: dict = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters dictionary

        Returns:
            List of query results
        """
        if parameters is None:
            parameters = {}

        try:
            # Use the Neo4jGraph query method which handles session management
            result = self.graph.query(query, parameters)
            logger.debug(f"Query executed successfully, returned {len(result)} results")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}", exc_info=True)
            raise

    def close(self) -> None:
        """Close the database connection."""
        # Connection is managed by the Database.Neo4j module
        logger.info("Database connection closure requested (managed by Database.Neo4j)")

    def __del__(self):
        """Ensure connection is properly handled when object is destroyed."""
        self.close()
