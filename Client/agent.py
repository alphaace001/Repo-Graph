from typing import TypedDict
from typing_extensions import Required, Annotated, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, ToolMessage, AIMessage, BaseMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode

from llm import llm


class AgentState(TypedDict):
    messages: Required[Annotated[list[AnyMessage], add_messages]]


def create_react(llm_with_tools):
    def model(state: AgentState):
        # print("INside model function")
        # print("State:", state["messages"][-1])
        response = llm_with_tools.invoke(state["messages"])
        if (
            response.response_metadata["finish_reason"] != "STOP"
            and response.response_metadata["finish_reason"] != "stop"
            and response.response_metadata["finish_reason"] != "tool_calls"
        ):
            print(
                "Invoking again due to incomplete response. Got response:",
                response.response_metadata["finish_reason"],
            )
            response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return model


def build_agent(tools: list):

    llm_with_tools = llm.bind_tools(tools)
    model = create_react(llm_with_tools)

    builder = StateGraph(AgentState)
    builder.add_node("model", model)
    builder.add_node("tools", ToolNode(tools=tools, handle_tool_errors=True))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")
    graph = builder.compile()
    return graph
