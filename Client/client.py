import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

from llm import llm
from agent import build_agent
from prompt import BASE_PROMPT

# Environment variables to suppress FastMCP banner
server_env = os.environ.copy()
server_env["FASTMCP_QUIET"] = "1"

SERVERS = {
    "analyst": {
        "transport": "stdio",
        "command": "D:/KGassign/KG-Assignment/.venv/Scripts/python.exe",
        "args": [
            "D:/KGassign/KG-Assignment/MCP/Analyst/main.py",
        ],
        "env": server_env,
    },
    "graph-query": {
        "transport": "stdio",
        "command": "D:/KGassign/KG-Assignment/.venv/Scripts/python.exe",
        "args": [
            "D:/KGassign/KG-Assignment/MCP/Graph_Query/main.py",
        ],
        "env": server_env,
    },
    "indexer": {
        "transport": "stdio",
        "command": "D:/KGassign/KG-Assignment/.venv/Scripts/python.exe",
        "args": [
            "D:/KGassign/KG-Assignment/MCP/Indexer/main.py",
        ],
        "env": server_env,
    },
}


async def main():
    try:
        client = MultiServerMCPClient(SERVERS)

        # List all available tools from all servers
        print("Connecting to MCP servers...")
        tools = await client.get_tools()
        # print(f"\nAvailable Tools ({len(tools)} total):")
        # for tool in tools:
        #     print(f"  - {tool.name}: {tool.description}")

        agent = build_agent(tools)
        messages = [
            (
                "system",
                BASE_PROMPT,
            ),
            ("human", "Compare how Path and Query parameters are implemented"),
        ]
        response = await agent.ainvoke({"messages": messages}, {"recursion_limit": 150})
        print(response["messages"][-1].content)
        return response["messages"][-1].content

        # llm_with_tools = llm.bind_tools(tools)
        # response = await llm_with_tools.ainvoke("What tools do you have")
        # print("Response:", response.content)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
