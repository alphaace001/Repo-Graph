"""
Test suite for Graph Query MCP - Entity finding and searching
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from Utils.query_service import GraphQueryService


class TestFindEntity(unittest.TestCase):
    """Test entity finding functionality."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_find_entity_by_name(self):
        """Test finding entity by exact name."""
        results = self.service.find_entity("APIRouter")
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("name", results[0])
            self.assertIn("type", results[0])

    def test_find_entity_by_partial_name(self):
        """Test finding entity by partial name."""
        results = self.service.find_entity("Router")
        self.assertIsInstance(results, list)
        # Should find APIRouter and possibly others

    def test_find_entity_by_type_filter(self):
        """Test finding entity with type filter."""
        results = self.service.find_entity("APIRouter", entity_type="Class")
        self.assertIsInstance(results, list)
        # Results should be Classes or empty

    def test_find_entity_nonexistent(self):
        """Test finding nonexistent entity."""
        results = self.service.find_entity("NonExistentEntity12345")
        self.assertIsInstance(results, list)
        # Should return empty list, not error

    def test_find_entity_empty_name(self):
        """Test finding entity with empty name."""
        results = self.service.find_entity("")
        self.assertIsInstance(results, list)

    def test_find_entity_special_characters(self):
        """Test finding entity with special characters in name."""
        results = self.service.find_entity("__init__")
        self.assertIsInstance(results, list)


class TestEntityByType(unittest.TestCase):
    """Test finding entities by type."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_find_functions(self):
        """Test finding all functions."""
        results = self.service.find_entity_by_type("Function")
        self.assertIsInstance(results, list)
        if results:
            for entity in results:
                self.assertEqual(entity["type"], "Function")

    def test_find_classes(self):
        """Test finding all classes."""
        results = self.service.find_entity_by_type("Class")
        self.assertIsInstance(results, list)
        if results:
            for entity in results:
                self.assertEqual(entity["type"], "Class")

    def test_find_modules(self):
        """Test finding all modules."""
        results = self.service.find_entity_by_type("Module")
        self.assertIsInstance(results, list)
        if results:
            for entity in results:
                self.assertEqual(entity["type"], "Module")


if __name__ == "__main__":
    unittest.main()
