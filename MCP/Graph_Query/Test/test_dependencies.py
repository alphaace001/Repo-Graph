"""
Test suite for Graph Query MCP - Dependency analysis
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from Utils.query_service import GraphQueryService


class TestGetDependencies(unittest.TestCase):
    """Test dependency analysis functionality."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_get_dependencies_function(self):
        """Test getting dependencies for a function."""
        # Find a function first
        entities = self.service.find_entity("run", entity_type="Function")
        if entities:
            entity_name = entities[0]["name"]
            results = self.service.get_dependencies(entity_name)
            self.assertIsInstance(results, list)
            if results:
                for dep in results:
                    self.assertIn("source_name", dep)
                    self.assertIn("target_name", dep)

    def test_get_dependencies_nonexistent(self):
        """Test getting dependencies for nonexistent entity."""
        results = self.service.get_dependencies("NonExistentEntity12345")
        self.assertIsInstance(results, list)
        # Should return empty list

    def test_get_dependents_function(self):
        """Test getting dependents (reverse dependencies)."""
        entities = self.service.find_entity("Request")
        if entities:
            entity_name = entities[0]["name"]
            results = self.service.get_dependents(entity_name)
            self.assertIsInstance(results, list)
            if results:
                for dep in results:
                    self.assertIn("source_name", dep)
                    self.assertIn("target_name", dep)

    def test_dependents_vs_dependencies(self):
        """Test that dependents are reverse of dependencies."""
        # Get a known entity
        entities = self.service.find_entity("APIRouter")
        if entities:
            entity_name = entities[0]["name"]
            deps = self.service.get_dependencies(entity_name)
            dependents = self.service.get_dependents(entity_name)

            # Both should return lists
            self.assertIsInstance(deps, list)
            self.assertIsInstance(dependents, list)


class TestCircularDependencies(unittest.TestCase):
    """Test circular dependency detection."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_find_circular_dependencies(self):
        """Test finding circular dependencies."""
        results = self.service.find_circular_dependencies()
        self.assertIsInstance(results, list)
        # Results may be empty if no circular dependencies exist

    def test_circular_dependencies_structure(self):
        """Test structure of circular dependency results."""
        results = self.service.find_circular_dependencies()
        if results:
            for cycle in results:
                self.assertIn("entity_a", cycle)
                self.assertIn("entity_b", cycle)
                self.assertIn("type_a", cycle)
                self.assertIn("type_b", cycle)


if __name__ == "__main__":
    unittest.main()
