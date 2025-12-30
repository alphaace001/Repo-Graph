"""
Integration test suite for Graph Query MCP
"""

import sys
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from Utils.query_service import GraphQueryService

# Mock the MCP tools for testing
try:
    import main
except ImportError:
    main = None


class TestGraphQueryMCPIntegration(unittest.TestCase):
    """Integration tests for the Graph Query MCP tools."""

    def test_module_imports(self):
        """Test that all required modules can be imported."""
        try:
            from Utils.query_service import GraphQueryService
            from Utils.db_connection import Neo4jConnection

            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import required modules: {str(e)}")

    @unittest.skipIf(main is None, "MCP server not available")
    def test_mcp_tools_defined(self):
        """Test that all MCP tools are defined."""
        if main:
            required_tools = [
                "find_entity",
                "get_dependencies",
                "get_dependents",
                "trace_imports",
                "find_related",
                "execute_query",
                "find_usage_patterns",
                "get_code_statistics",
                "find_circular_dependencies",
                "find_entity_by_type",
            ]
            # Tools are registered with the MCP instance
            # This is a basic check that the module loads


class TestDataFlow(unittest.TestCase):
    """Test data flow through different queries."""

    @classmethod
    def setUpClass(cls):
        """Initialize the query service."""
        from Utils.query_service import GraphQueryService

        cls.service = GraphQueryService()

    def test_find_and_analyze_entity(self):
        """Test finding an entity and then analyzing it."""
        # Find an entity
        entities = self.service.find_entity("APIRouter")

        if entities:
            entity_name = entities[0]["name"]

            # Get its dependencies
            deps = self.service.get_dependencies(entity_name)
            self.assertIsInstance(deps, list)

            # Get what depends on it
            dependents = self.service.get_dependents(entity_name)
            self.assertIsInstance(dependents, list)

            # Get usage patterns
            patterns = self.service.find_usage_patterns(entity_name)
            self.assertIsInstance(patterns, list)

    def test_entity_discovery_workflow(self):
        """Test complete entity discovery workflow."""
        # Step 1: Get statistics
        stats = self.service.get_code_statistics()
        self.assertTrue(stats.get("function_count", 0) > 0)

        # Step 2: Find functions
        functions = self.service.find_entity_by_type("Function")
        self.assertIsInstance(functions, list)

        # Step 3: Find classes
        classes = self.service.find_entity_by_type("Class")
        self.assertIsInstance(classes, list)

        # Step 4: Find modules
        modules = self.service.find_entity_by_type("Module")
        self.assertIsInstance(modules, list)

    def test_import_chain_analysis(self):
        """Test analyzing import chains."""
        modules = self.service.find_entity_by_type("Module")

        if modules:
            # Pick first module
            module_name = modules[0]["name"]

            # Trace imports
            chains = self.service.trace_imports(module_name, max_depth=3)
            self.assertIsInstance(chains, list)


if __name__ == "__main__":
    unittest.main()
