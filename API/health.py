"""
Health Checker Module - Verifies Knowledge Graph and MCP Services Status
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from neo4j import GraphDatabase
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

# Setup Python paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import setup_logger
from config import (
    MCP_SERVERS,
    SERVICE_NAMES,
    NEO4J_URL,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    HEALTH_CHECK_TIMEOUT,
)

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)


class HealthChecker:
    """Health checker for Knowledge Graph and MCP services"""

    def __init__(self):
        """Initialize health checker with service endpoints"""
        # Neo4j configuration
        self.neo4j_url = NEO4J_URL
        self.neo4j_username = NEO4J_USERNAME
        self.neo4j_password = NEO4J_PASSWORD

        self.timeout = HEALTH_CHECK_TIMEOUT  # seconds

        # Service display names
        self.service_names = SERVICE_NAMES

        # MCP Server configurations (for MultiServerMCPClient)
        self.mcp_services = MCP_SERVERS

    async def check_knowledge_graph(self) -> bool:
        """
        Check if Knowledge Graph (Neo4j) is live

        Returns:
            bool: True if graph is accessible, False otherwise
        """
        try:

            logger.debug("Checking Knowledge Graph connectivity...")

            # Extract host and port from neo4j URL
            # Format: neo4j://host:port or bolt://host:port
            url_parts = self.neo4j_url.replace("neo4j://", "").replace("bolt://", "")

            driver = GraphDatabase.driver(
                self.neo4j_url,
                auth=(self.neo4j_username, self.neo4j_password),
                connection_timeout=self.timeout,
            )

            # Test connection with a simple query
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.consume()

            driver.close()
            logger.info("Knowledge Graph is live")
            return True

        except Exception as e:
            logger.warning(f" Knowledge Graph check failed: {str(e)}")
            return False

    async def check_mcp_service(self, service_name: str) -> bool:
        """
        Check if a specific MCP service is live by attempting to connect and retrieve tools

        Args:
            service_name: Name of the service (graph_query, analyst, or indexer)

        Returns:
            bool: True if service is responding and tools retrieved, False otherwise
        """
        if service_name not in self.mcp_services:
            logger.error(f"Unknown service: {service_name}")
            return False

        service_display_name = self.service_names.get(service_name, service_name)

        try:
            logger.debug(f"Checking {service_display_name} connectivity...")

            # Create a single-server client for this service
            servers_config = {service_name: self.mcp_services[service_name]}
            client = MultiServerMCPClient(servers_config)

            # Try to connect and retrieve tools - if successful, service is up
            tools = await asyncio.wait_for(client.get_tools(), timeout=self.timeout)

            if tools is not None and len(tools) > 0:
                logger.info(
                    f"{service_display_name} is live (retrieved {len(tools)} tools)"
                )
                return True
            else:
                logger.warning(f" {service_display_name} returned no tools")
                return False

        except asyncio.TimeoutError:
            logger.warning(f" {service_display_name} health check timed out")
            return False
        except BaseException as e:
            # Catch all exceptions including TaskGroup errors
            error_msg = str(e).split("\n")[0] if str(e) else str(type(e).__name__)
            logger.warning(f" {service_display_name} check failed: {error_msg}")
            return False

    async def check_mcp_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Check all MCP services in parallel

        Returns:
            Dict with status of each service
        """
        logger.debug("Checking all MCP services...")

        results = {}

        # Check all services in parallel
        tasks = {
            service_name: self.check_mcp_service(service_name)
            for service_name in self.mcp_services.keys()
        }

        # Wait for all tasks to complete
        for service_name, task in tasks.items():
            service_display_name = self.service_names.get(service_name, service_name)
            try:
                is_live = await task
                results[service_name] = {
                    "status": "healthy" if is_live else "unhealthy",
                    "name": service_display_name,
                    "message": (
                        "Service is responding and tools available"
                        if is_live
                        else "Service is not responding or no tools available"
                    ),
                }
            except Exception as e:
                results[service_name] = {
                    "status": "unhealthy",
                    "name": service_display_name,
                    "message": f"Error: {str(e)}",
                }

        return results

    async def check_all_services(self) -> Dict[str, Any]:
        """
        Check all services (Knowledge Graph + MCP services)

        Returns:
            Dict with comprehensive health status
        """
        logger.debug("Running comprehensive health check...")

        # Check Knowledge Graph
        kg_alive = await self.check_knowledge_graph()

        # Check MCP services in parallel
        mcp_statuses = await self.check_mcp_services()

        # Calculate overall status
        mcp_healthy = all(
            service["status"] == "healthy" for service in mcp_statuses.values()
        )

        if kg_alive and mcp_healthy:
            overall_status = "healthy"
        elif kg_alive or mcp_healthy:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "knowledge_graph": {
                "status": "healthy" if kg_alive else "unhealthy",
                "name": "Neo4j Knowledge Graph",
                "url": self.neo4j_url,
                "message": (
                    "Knowledge Graph is live"
                    if kg_alive
                    else "Knowledge Graph is not accessible"
                ),
            },
            "mcp_services": mcp_statuses,
        }
