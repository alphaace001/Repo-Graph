"""
Neo4j graph operations service - Single Responsibility Principle.
Centralizes all graph query logic.
"""

from typing import Dict, Any, List, Optional

from logger import setup_logger

logger = setup_logger(__name__)


class GraphOperations:
    """Service for Neo4j graph operations following Single Responsibility Principle."""

    def __init__(self, graph):
        """
        Initialize GraphOperations service.

        Args:
            graph: Neo4jGraph instance
        """
        self.graph = graph

    def create_or_merge_node(
        self, node_type: str, properties: Dict[str, Any], return_field: str = "id"
    ) -> str:
        """
        Always CREATE a new node and set all properties.
        """
        set_clause = ", ".join([f"n.{k} = ${k}" for k in properties.keys()])

        query = f"""
        CREATE (n:{node_type})
        SET {set_clause}
        RETURN elementId(n) as {return_field}
        """

        result = self.graph.query(query, properties)
        return result[0][return_field] if result else None

    def create_relationship(
        self,
        source_type: str,
        source_id: str,
        rel_type: str,
        target_type: str,
        target_id: str,
    ) -> None:
        """
        Create a relationship between two nodes by element ID.

        Args:
            source_type: Source node label
            source_id: Source node element ID
            rel_type: Relationship type
            target_type: Target node label
            target_id: Target node element ID
        """
        query = f"""
        MATCH (s:{source_type})
        WHERE elementId(s) = $source_id
        
        MATCH (t:{target_type})
        WHERE elementId(t) = $target_id
        
        MERGE (s)-[:{rel_type}]->(t)
        """

        self.graph.query(query, {"source_id": source_id, "target_id": target_id})

    def create_docstring(
        self, entity_type: str, entity_id: str, docstring: str
    ) -> None:
        """
        Create and link a docstring node.

        Args:
            entity_type: Type of entity (e.g., 'Function', 'Class')
            entity_id: Element ID of the entity
            docstring: The docstring content
        """
        if not docstring or not docstring.strip():
            return

        doc_name = f"{entity_type.lower()}_{entity_id}_docstring"
        query = f"""
        MATCH (e:{entity_type})
        WHERE elementId(e) = $entity_id
        
        MERGE (d:Docstring {{name: $doc_name}})
        SET d.content = $doc_text
        
        MERGE (e)-[:DOCUMENTED_BY]->(d)
        """

        self.graph.query(
            query,
            {
                "entity_id": entity_id,
                "doc_name": doc_name,
                "doc_text": docstring,
            },
        )

    def create_parameter_node(
        self, entity_type: str, entity_id: str, param_name: str, kv_pair: str
    ) -> None:
        """
        Create or update a parameter node.

        Args:
            entity_type: Type of parent entity ('Function' or 'Method')
            entity_id: Element ID of the parent entity
            param_name: Name/identifier for the parameter group
            kv_pair: Key-value pair string (e.g., "name=str")
        """
        query = f"""
        MATCH (e:{entity_type})
        WHERE elementId(e) = $entity_id
        
        MERGE (p:Parameter {{name: $param_name}})
        SET p.pairs = coalesce(p.pairs, []) + $pair
        
        MERGE (e)-[:HAS_PARAMETER]->(p)
        """

        self.graph.query(
            query,
            {
                "entity_id": entity_id,
                "param_name": param_name,
                "pair": [kv_pair],
            },
        )

    def create_contains_relationship(
        self, container_type: str, container_id: str, child_type: str, child_id: str
    ) -> None:
        """
        Create a CONTAINS relationship.

        Args:
            container_type: Type of container (e.g., 'Module', 'Class')
            container_id: Element ID of container
            child_type: Type of child (e.g., 'Function', 'Method')
            child_id: Element ID of child
        """
        self.create_relationship(
            container_type, container_id, "CONTAINS", child_type, child_id
        )

    def create_import_relationship(
        self, source_module: str, target_module: str
    ) -> None:
        """
        Create an IMPORTS relationship between modules.

        Args:
            source_module: Source module name
            target_module: Target module name
        """
        query = """
        MATCH (source:Module {name: $source_file})
        MATCH (target:Module {name: $target_file})
        MERGE (source)-[:IMPORTS]->(target)
        """

        self.graph.query(
            query,
            {
                "source_file": source_module,
                "target_file": target_module,
            },
        )

    def create_decorated_by_relationship(
        self,
        source_type: str,
        source_id: str,
        decorator_fq: str,
        target_module: str,
    ) -> None:
        """
        Create a DECORATED_BY relationship with optional fallback targets.

        Args:
            source_type: Type of decorated entity ('Function', 'Class', 'Method')
            source_id: Element ID of decorated entity
            decorator_fq: Fully-qualified decorator name (e.g., 'package.module.decorator')
            target_module: Target module name
        """
        if "." not in decorator_fq:
            return

        module_path, symbol_name = decorator_fq.rsplit(".", 1)

        query = f"""
        MATCH (e:{source_type})
        WHERE elementId(e) = $entity_id
        
        MATCH (m:Module {{name: $module_path}})
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {{name: $symbol_name}})
        WHERE target_func.parent_function IS NULL
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {{name: $symbol_name}})
        
        WITH e, target_func, target_class
        WHERE target_func IS NOT NULL OR target_class IS NOT NULL
        
        FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
            MERGE (e)-[:DECORATED_BY]->(target_func)
        )
        
        FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
            MERGE (e)-[:DECORATED_BY]->(target_class)
        )
        """

        self.graph.query(
            query,
            {
                "entity_id": source_id,
                "module_path": target_module,
                "symbol_name": symbol_name,
            },
        )
