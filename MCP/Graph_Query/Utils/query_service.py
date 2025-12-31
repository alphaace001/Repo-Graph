"""
Graph Query Service - Executes Cypher queries for knowledge graph traversal.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import get_mcp_safe_logger
from Database.Neo4j.initialise import graph

logger = get_mcp_safe_logger(__name__)


class GraphQueryService:
    """Service for executing knowledge graph queries against Neo4j."""

    def __init__(self):
        """Initialize with database connection."""
        self.db = graph

    def find_entity(self, name: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find an entity by name, optionally filtered by type.

        Args:
            name: Entity name to search for
            entity_type: Optional entity type filter of "Function", "Class", "Module","Docstring","Method","Parameter" only

        Returns:
            List of matching entities with their properties
        """
        # Validate entity_type if provided

        valid_types = ["Function", "Class", "Module", "Docstring", "Method", "Parameter"]
        if entity_type and entity_type not in valid_types:
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(valid_types)}"
            )

        if entity_type:
            query = f"""
            MATCH (entity:{entity_type})
            WHERE entity.name CONTAINS $name
            RETURN 
                entity.name as name,
                labels(entity)[0] as type,
                entity as properties,
                elementId(entity) as id
            LIMIT 20
            """
            logger.info(f"Searching for {entity_type} entities with name containing '{name}'")
        else:
            query = """
            MATCH (entity)
            WHERE entity.name CONTAINS $name
            AND (entity:Function OR entity:Class OR entity:Module)
            RETURN 
                entity.name as name,
                labels(entity)[0] as type,
                entity as properties,
                elementId(entity) as id
            LIMIT 20
            """
            logger.info(f"Searching for any entity with name containing '{name}'")

        try:
            results = self.db.query(query, {"name": name})
            logger.info(f"Found {len(results)} entities matching '{name}'")
            return results
        except Exception as e:
            logger.error(f"Error finding entity '{name}': {str(e)}")
            raise

    def get_dependencies(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Find what an entity depends on (DEPENDS_ON relationships).

        Args:
            entity_id: ID of the entity

        Returns:
            List of dependencies
        """
        query = """
        MATCH (source)-[rel:DEPENDS_ON]->(target)
        WHERE elementId(source) = $entity_id
        RETURN 
            source.name AS source_name,
            labels(source)[0] AS source_type,
            type(rel) AS relationship,
            target.name AS target_name,
            labels(target)[0] AS target_type,
            elementId(target) AS target_id
        """

        try:
            results = self.db.query(query, {"entity_id": entity_id})
            logger.info(f"Found {len(results)} dependencies for entity '{entity_id}'")
            return results
        except Exception as e:
            logger.error(f"Error getting dependencies for entity '{entity_id}': {str(e)}")
            raise (f"Error getting dependencies for entity '{entity_id}': {str(e)}")

    def get_dependents(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Find what depends on an entity (reverse DEPENDS_ON relationships).

        Args:
            entity_id: ID of the entity

        Returns:
            List of entities that depend on this one
        """
        query = """
        MATCH (source)-[rel:DEPENDS_ON]->(target)
        WHERE elementId(target) = $entity_id
        RETURN 
            source.name AS source_name,
            labels(source)[0] AS source_type,
            elementId(source) AS source_id,
            type(rel) AS relationship,
            target.name AS target_name,
            labels(target)[0] AS target_type
        """

        try:
            results = self.db.query(query, {"entity_id": entity_id})
            logger.info(f"Found {len(results)} dependents of '{entity_id}'")
            return results
        except Exception as e:
            logger.error(f"Error getting dependents for '{entity_id}': {str(e)}")
            raise (f"Error getting dependents for '{entity_id}': {str(e)}")

    def trace_imports(self, module_name: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Trace import chain for a module (BFS traversal).

        Args:
            module_name: Name of the module
            max_depth: Maximum depth for traversal

        Returns:
            List of import chains
        """
        query = (
            """
        MATCH path = (start:Module {name: $module_name})-[:IMPORTS*1..%d]->(end:Module)
        RETURN 
            start.name as source_module,
            end.name as target_module,
            length(path) - 1 as depth,
            [node in nodes(path) | node.name] as import_chain
        ORDER BY depth
        """
            % max_depth
        )

        try:
            results = self.db.query(query, {"module_name": module_name})
            logger.info(f"Found {len(results)} import paths for module '{module_name}'")
            return results
        except Exception as e:
            logger.error(f"Error tracing imports for '{module_name}': {str(e)}")
            raise

    def find_related(self, entity_id: str, relationship_type: str) -> List[Dict[str, Any]]:
        """
        Find entities related by a specified relationship type.

        Args:
            entity_id: ID of the source entity
            relationship_type: Type of relationship "CONTAINS","DEPENDS_ON","DOCUMENTED_BY","HAS_PARAMETER","IMPORTS","INHERITS_FROM" Only

        Returns:
            List of related entities
        """

        # Sanitize relationship type to prevent injection
        safe_rel_type = "".join(c for c in relationship_type if c.isalnum() or c == "_")
        valid_types = [
            "CONTAINS",
            "DEPENDS_ON",
            "DOCUMENTED_BY",
            "HAS_PARAMETER",
            "IMPORTS",
            "INHERITS_FROM",
            "DECORATED_BY",
        ]
        if relationship_type and relationship_type not in valid_types:
            logger.warning(f"Invalid relationship_type '{relationship_type}', ignoring filter")
            raise ValueError(f"Invalid relationship type: {relationship_type}")

        query = f"""
        MATCH (source)-[rel:{safe_rel_type}]->(target)
        WHERE elementId(source) = $entity_id
        RETURN 
            source.name as source_name,
            labels(source)[0] as source_type,
            $rel_type as relationship,
            target.name as target_name,
            labels(target)[0] as target_type,
            elementId(target) as target_id
        UNION
        MATCH (source)-[rel:{safe_rel_type}]->(target)
        WHERE elementId(target) = $entity_id
        RETURN 
            source.name as source_name,
            labels(source)[0] as source_type,
            $rel_type as relationship,
            target.name as target_name,
            labels(target)[0] as target_type,
            elementId(target) as target_id
        """

        try:
            results = self.db.query(
                query, {"entity_id": entity_id, "rel_type": relationship_type}
            )
            logger.info(
                f"Found {len(results)} entities related by '{relationship_type}' to entity '{entity_id}'"
            )
            return results
        except Exception as e:
            logger.error(f"Error finding related entities for '{entity_id}': {str(e)}")
            raise (f"Error finding related entities for '{entity_id}': {str(e)}")

    def execute_custom_query(self, query: str, parameters: dict = None) -> List[Dict[str, Any]]:
        """
        Execute a custom Cypher query with safety constraints.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query results

        Raises:
            ValueError: If query contains dangerous operations
        """
        if parameters is None:
            parameters = {}

        # Safety checks to prevent destructive operations
        dangerous_keywords = ["DELETE", "REMOVE", "SET", "CREATE", "MERGE"]
        query_upper = query.upper().strip()

        if any(query_upper.startswith(kw) for kw in dangerous_keywords):
            raise ValueError(
                f"Query execution not allowed. Detected destructive operation: {query_upper.split()[0]}"
            )

        if "CALL dbms" in query_upper or "CALL apoc.load" in query_upper:
            raise ValueError("System procedure calls not allowed for security reasons")

        try:
            results = self.db.query(query, parameters)
            logger.info(f"Custom query executed successfully, returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error executing custom query: {str(e)}")
            raise

    def get_code_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the indexed codebase.

        Returns:
            Dictionary with codebase statistics
        """
        query = """
        RETURN
            count(DISTINCT n:Module) as module_count,
            count(DISTINCT n:Function) as function_count,
            count(DISTINCT n:Class) as class_count,
            count(DISTINCT r:DEPENDS_ON) as dependency_count,
            count(DISTINCT r:IMPORTS) as import_count
        """

        try:
            results = self.db.query(query)
            if results:
                return results[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting code statistics: {str(e)}")
            raise

    def find_circular_dependencies(self) -> List[Dict[str, Any]]:
        """
        Find circular dependencies in the codebase.

        Returns:
            List of circular dependency paths
        """
        query = """
        MATCH (a)-[:DEPENDS_ON]->(b)-[:DEPENDS_ON*]->(a)
        RETURN 
            a.name as entity_a,
            labels(a)[0] as type_a,
            b.name as entity_b,
            labels(b)[0] as type_b
        LIMIT 50
        """

        try:
            results = self.db.query(query)
            logger.info(f"Found {len(results)} circular dependencies")
            return results
        except Exception as e:
            logger.error(f"Error finding circular dependencies: {str(e)}")
            raise

    def find_entity_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Find all entities of a specific type.

        Args:
            entity_type: Type of entity (Function, Class, Module)

        Returns:
            List of entities
        """
        query = f"""
        MATCH (entity:{entity_type})
        RETURN 
            entity.name as name,
            labels(entity)[0] as type,
            elementId(entity) as id
        LIMIT 100
        """

        try:
            results = self.db.query(query)
            logger.info(f"Found {len(results)} entities of type '{entity_type}'")
            return results
        except Exception as e:
            logger.error(f"Error finding entities of type '{entity_type}': {str(e)}")
            raise
