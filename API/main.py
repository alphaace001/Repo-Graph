"""
FastAPI Backend Server with Health Check API
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Setup Python paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "Database"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Client"))

# Load environment variables
load_dotenv()

from logger import setup_logger
from health import HealthChecker
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import MCP_SERVERS, API_PORT, API_HOST, AGENT_RECURSION_LIMIT

from Client.llm import llm
from Client.agent import build_agent
from Client.prompt import BASE_PROMPT


# Setup logger
logger = setup_logger(__name__)


# Pydantic Models
class HealthResponse(BaseModel):
    status: str
    knowledge_graph: Dict[str, Any]
    mcp_services: Dict[str, Dict[str, Any]]
    timestamp: str


class ServiceStatus(BaseModel):
    status: str
    message: str


class ChatRequest(BaseModel):
    """Chat request model"""

    query: str


class ChatResponse(BaseModel):
    """Chat response model"""

    response: str
    status: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    logger.info("FastAPI Backend Server starting...")

    # Initialize MCP Client and Agent FIRST
    try:
        logger.info("Initializing MCP Client and Agent...")
        client = MultiServerMCPClient(MCP_SERVERS)
        app.state.mcp_client = client

        logger.info("Connecting to MCP servers and retrieving tools...")
        tools = await client.get_tools()
        
        if tools:
            logger.info(f"Retrieved {len(tools)} tools from MCP servers")
            app.state.agent = build_agent(tools)
            logger.info("Agent built and bound successfully")
        else:
            logger.warning("No tools retrieved from MCP servers - Agent will not be available")
            app.state.agent = None
            
    except Exception as e:
        logger.error(f"Failed to initialize MCP Client/Agent: {e}", exc_info=True)
        app.state.agent = None

    # Run health check using the initialized client
    try:
        logger.info("Running startup health check...")
        
        # Pass the initialized client to health checker
        client = getattr(app.state, "mcp_client", None)
        health_status = await health_checker.check_all_services(client=client)

        if health_status["overall_status"] == "healthy":
            logger.info("All services are healthy - Server ready")
        elif health_status["overall_status"] == "degraded":
            logger.warning("Some services are degraded but server is operational")
        else:
            logger.error(
                "Critical services are unavailable - Server may not function properly"
            )

    except Exception as e:
        logger.error(f"Startup health check failed: {str(e)}")

    yield
    logger.info("FastAPI Backend Server shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Graph Backend API",
    description="FastAPI server for Knowledge Graph with health checks",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize health checker
health_checker = HealthChecker()

# MCP Servers configuration for chat endpoint (shared from config)
SERVERS = MCP_SERVERS


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Knowledge Graph Backend API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies:
    - Knowledge Graph (Neo4j) connectivity
    - All 3 MCP services (Graph_Query, Analyst, Indexer)
    """
    logger.info("Health check requested")

    try:
        health_status = await health_checker.check_all_services()

        if health_status["overall_status"] == "healthy":
            return JSONResponse(
                status_code=200,
                content=health_status,
            )
        else:
            return JSONResponse(
                status_code=503,
                content=health_status,
            )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "message": "Health check encountered an error",
            },
        )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, raw_request: Request):
    """
    Send a message and receive a response from the AI agent.

    The agent uses MCP services to analyze the codebase and provide insights.

    Args:
        request: ChatRequest with user query

    Returns:
        ChatResponse with AI agent response
    """

    logger.info(f"Chat request received: {request.query}")

    try:
        # Check if agent is initialized in app state
        agent = getattr(raw_request.app.state, "agent", None)
        
        if not agent:
             logger.warning("Agent not initialized in app state")
             return JSONResponse(
                 status_code=503,
                 content={
                     "status": "error",
                     "response": "AI Agent not initialized. Please check server logs.",
                 },
             )

        # Prepare messages with user query
        messages = [
            ("system", BASE_PROMPT),
            ("human", request.query),
        ]

        logger.debug(f"Invoking agent with query: {request.query}")

        # Invoke agent
        response = await agent.ainvoke(
            {"messages": messages}, {"recursion_limit": AGENT_RECURSION_LIMIT}
        )

        # Extract response from agent
        agent_response = response["messages"][-1].content

        logger.info("Chat response generated successfully")

        return ChatResponse(
            response=agent_response,
            status="success",
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "response": f"Error processing request: {str(e)}",
            },
        )


if __name__ == "__main__":
    import uvicorn

    port = API_PORT
    host = API_HOST

    logger.info(f"Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
