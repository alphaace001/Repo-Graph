"""
Test suite for Graph Query MCP - Custom queries and statistics
"""

import sys
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from Utils.query_service import GraphQueryService


class TestCustomQueries(unittest.TestCase):
    """Test custom query execution."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_execute_valid_query(self):
        """Test executing a valid read-only query."""
        query = "MATCH (n:Module) RETURN count(n) as count LIMIT 1"
        results = self.service.execute_custom_query(query)
        self.assertIsInstance(results, list)

    def test_execute_query_with_parameters(self):
        """Test executing query with parameters."""
        query = """
        MATCH (m:Module {name: $module_name})
        RETURN m.name as name
        """
        results = self.service.execute_custom_query(query, {"module_name": "fastapi"})
        self.assertIsInstance(results, list)

    def test_execute_query_blocks_delete(self):
        """Test that DELETE queries are blocked."""
        query = "MATCH (n:Module) DELETE n"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_query_blocks_remove(self):
        """Test that REMOVE queries are blocked."""
        query = "MATCH (n:Module) REMOVE n.name"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_query_blocks_set(self):
        """Test that SET queries are blocked."""
        query = "MATCH (n:Module) SET n.name = 'test'"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_query_blocks_create(self):
        """Test that CREATE queries are blocked."""
        query = "CREATE (n:Module {name: 'test'})"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_query_blocks_merge(self):
        """Test that MERGE queries are blocked."""
        query = "MERGE (n:Module {name: 'test'})"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_query_blocks_system_procedures(self):
        """Test that system procedures are blocked."""
        query = "CALL dbms.components()"
        with self.assertRaises(ValueError):
            self.service.execute_custom_query(query)

    def test_execute_match_query(self):
        """Test executing a MATCH query."""
        query = """
        MATCH (f:Function)
        RETURN f.name as name
        LIMIT 5
        """
        results = self.service.execute_custom_query(query)
        self.assertIsInstance(results, list)

    def test_execute_where_clause(self):
        """Test executing query with WHERE clause."""
        query = """
        MATCH (n:Function)
        WHERE n.name CONTAINS 'run'
        RETURN n.name as name
        LIMIT 10
        """
        results = self.service.execute_custom_query(query)
        self.assertIsInstance(results, list)

    def test_execute_complex_query(self):
        """Test executing a complex query."""
        query = """
        MATCH (m:Module)-[:CONTAINS]->(f:Function)
        WHERE f.name CONTAINS 'get'
        RETURN m.name as module, f.name as function
        LIMIT 20
        """
        results = self.service.execute_custom_query(query)
        self.assertIsInstance(results, list)


class TestStatistics(unittest.TestCase):
    """Test codebase statistics."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_get_statistics(self):
        """Test getting codebase statistics."""
        stats = self.service.get_code_statistics()
        self.assertIsInstance(stats, dict)

    def test_statistics_fields(self):
        """Test that statistics contain expected fields."""
        stats = self.service.get_code_statistics()
        expected_fields = [
            "module_count",
            "function_count",
            "class_count",
            "dependency_count",
            "import_count",
        ]
        for field in expected_fields:
            self.assertIn(field, stats)

    def test_statistics_values_positive(self):
        """Test that statistic values are positive integers."""
        stats = self.service.get_code_statistics()
        for key, value in stats.items():
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in various scenarios."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_invalid_query_syntax(self):
        """Test error handling for invalid query syntax."""
        query = "INVALID QUERY SYNTAX"
        with self.assertRaises(Exception):
            self.service.execute_custom_query(query)

    def test_empty_query(self):
        """Test empty query handling."""
        query = ""
        with self.assertRaises(Exception):
            self.service.execute_custom_query(query)


if __name__ == "__main__":
    unittest.main()
