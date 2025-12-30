"""
Test suite for Graph Query MCP - Relationship and import tracing
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from Utils.query_service import GraphQueryService


class TestTraceImports(unittest.TestCase):
    """Test import chain tracing."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_trace_imports_valid_module(self):
        """Test tracing imports for a valid module."""
        # Try tracing imports for a known module
        modules = self.service.find_entity_by_type("Module")
        if modules:
            module_name = modules[0]["name"]
            results = self.service.trace_imports(module_name, max_depth=3)
            self.assertIsInstance(results, list)

    def test_trace_imports_max_depth(self):
        """Test trace imports respects max_depth."""
        modules = self.service.find_entity_by_type("Module")
        if modules:
            module_name = modules[0]["name"]
            results = self.service.trace_imports(module_name, max_depth=2)
            if results:
                for path in results:
                    self.assertLessEqual(path.get("depth", 0), 2)

    def test_trace_imports_invalid_depth(self):
        """Test trace imports with invalid depth (should clamp)."""
        modules = self.service.find_entity_by_type("Module")
        if modules:
            module_name = modules[0]["name"]
            # Try invalid depth (too large)
            results = self.service.trace_imports(module_name, max_depth=50)
            self.assertIsInstance(results, list)


class TestFindRelated(unittest.TestCase):
    """Test finding related entities."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_find_related_imports(self):
        """Test finding entities related by IMPORTS."""
        modules = self.service.find_entity_by_type("Module")
        if modules:
            module_name = modules[0]["name"]
            results = self.service.find_related(module_name, "IMPORTS")
            self.assertIsInstance(results, list)

    def test_find_related_inherits_from(self):
        """Test finding entities related by INHERITS_FROM."""
        classes = self.service.find_entity_by_type("Class")
        if classes:
            class_name = classes[0]["name"]
            results = self.service.find_related(class_name, "INHERITS_FROM")
            self.assertIsInstance(results, list)

    def test_find_related_depends_on(self):
        """Test finding entities related by DEPENDS_ON."""
        functions = self.service.find_entity_by_type("Function")
        if functions:
            func_name = functions[0]["name"]
            results = self.service.find_related(func_name, "DEPENDS_ON")
            self.assertIsInstance(results, list)

    def test_find_related_decorated_by(self):
        """Test finding entities related by DECORATED_BY."""
        functions = self.service.find_entity_by_type("Function")
        if functions:
            func_name = functions[0]["name"]
            results = self.service.find_related(func_name, "DECORATED_BY")
            self.assertIsInstance(results, list)

    def test_find_related_invalid_type(self):
        """Test find related with invalid relationship type."""
        entities = self.service.find_entity("APIRouter")
        if entities:
            entity_name = entities[0]["name"]
            # Should handle gracefully or return empty
            results = self.service.find_related(entity_name, "NONEXISTENT")
            self.assertIsInstance(results, list)


class TestUsagePatterns(unittest.TestCase):
    """Test usage pattern analysis."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        cls.service = GraphQueryService()

    def test_find_usage_patterns(self):
        """Test finding usage patterns for an entity."""
        entities = self.service.find_entity("APIRouter")
        if entities:
            entity_name = entities[0]["name"]
            results = self.service.find_usage_patterns(entity_name)
            self.assertIsInstance(results, list)
            if results:
                pattern = results[0]
                self.assertIn("entity_name", pattern)

    def test_usage_patterns_structure(self):
        """Test structure of usage patterns."""
        entities = self.service.find_entity("Request")
        if entities:
            entity_name = entities[0]["name"]
            results = self.service.find_usage_patterns(entity_name)
            if results:
                pattern = results[0]
                # Check for various usage relationship fields
                self.assertTrue(
                    any(
                        key in pattern
                        for key in [
                            "depended_by",
                            "decorated_by",
                            "inherited_by",
                            "contains",
                            "imports",
                        ]
                    )
                )


if __name__ == "__main__":
    unittest.main()
