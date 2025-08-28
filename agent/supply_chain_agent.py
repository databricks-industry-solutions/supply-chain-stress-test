from typing import Any, Optional, Sequence, Union
import os
import json
import mlflow
import pandas as pd
from databricks_langchain import ChatDatabricks
from databricks_langchain import (
    DatabricksFunctionClient,
    UCFunctionToolkit,
    set_uc_function_client,
)
from databricks.sdk import WorkspaceClient
from langchain_core.language_models import LanguageModelLike
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt.tool_node import ToolNode
from mlflow.langchain.chat_agent_langgraph import ChatAgentState, ChatAgentToolNode
from mlflow.models import ModelConfig
from mlflow.pyfunc import ChatAgent
from mlflow.types.agent import (
    ChatAgentMessage,
    ChatAgentResponse,
    ChatContext,
)

import random, string, math
from itertools import product
from collections import defaultdict
import pyomo.environ as pyo
import scripts.utils as utils


mlflow.langchain.autolog()

LLM_ENDPOINT = "databricks-llama-4-maverick"
config = {
    "endpoint_name": LLM_ENDPOINT,
    "catalog": "supply_chain_stress_test",
    "database": "data",
    "volume": "operational",
    "temperature": 0.01,
    "max_tokens": 1000,
    "system_prompt": """
    "You are a helpful assistant that answers questions about a supply chain network. Questions outside this topic are considered irrelevant. You use a set of tools to provide answers, and if needed, you ask the user follow up questions to clarify their request.

    Below are the definitions of the model parameters:
    Parameters            | What it represents                                                                              --------------------- | -------------------------------------------------------------------------------------------------- | tier1 / tier2 / tier3 | Lists of node IDs in each tier.                                                                    |edges                 | Directed links `(source, target)` showing which node supplies which.                               |material_type         | List of all material types.                                                                        |
    supplier_material_type| Material type each supplier produces and supplies.                                                 |
    f                     | Profit margin for each Tier 1 node’s finished product.                                             |
    s                     | On-hand inventory units at every node.                                                             |
    d                     | Demand per time unit for Tier 1 products.                                                          |
    c                     | Production capacity per time unit at each node.                                                    |
    r                     | Number of material types (k) required to make one unit of node j.                                  |
    N_minus               | For each node j (Tier 1 or 2), the set of material types it requires.                              |
    N_plus                | For each supplier i (Tier 2 or 3), the set of downstream nodes j it feeds.                         |
    P                     | For each (j, material_part) pair, a list of upstream suppliers i that provides it (multi-sourcing view). |
    
    And the definitions of decision variables:
    Decision Variables    | What it represents                                                                              --------------------- | -------------------------------------------------------------------------------------------------- | 
    l                     | Production volume lost of the product of the node.                                                 |u                     | Total production volume of the node during the ttr.                                                |y                     | Allocation of upstream node to downsteam node during the ttr.                                      |
    
    Do not forget to report the profit loss during the recovery period. When providing recommendations, base them on the interpretation of the decision variables and summarize the best actions for this scenario. Provide precise numbers whenever possible.
    """,
}

@tool
@mlflow.trace(name="TTR", span_type=mlflow.entities.SpanType.TOOL)
def ttr_agent_tool(
    disrupted: list[str],
    ttr: float,
    catalog: str = config["catalog"],
    database: str = config["database"],
    volume: str = config["volume"],
    ) -> str:
    """
    Runs an optimization algorithm for a given disrupted scenario and returns the results as a string.

    Parameters:
    disrupted (list[str]): List of disrupted nodes in the scenario.
    ttr (float): Time to recover (TTR) for the disruption scenario.
    catalog (str): Catalog name for Unity Catalog.
    database (str): Database name in Unity Catalog.
    volume (str): Volume name in Unity Catalog.
    
    Returns:
    str: A string representation of the optimization results.
    """    
    # Get the operational data from Unity Catalog Volume
    w = WorkspaceClient(host=os.getenv("HOST"), token=os.getenv("TOKEN"))
    path = f'/Volumes/{catalog}/{database}/{volume}/dataset_small.json'
    resp = w.files.download(path)  # returns DownloadResponse with a BinaryIO at .contents
    with resp.contents as fh:
        dataset = json.load(fh)   # `data` is now a Python dict/list

    # Build and solve TTR
    df = utils.build_and_solve_ttr(dataset, disrupted, ttr, True)
    model = df["model"].values[0]
    records = []
    for v in model.component_data_objects(ctype=pyo.Var, active=True):
        idx  = v.index()
        record  = {
            "var_name"  : v.parent_component().name,
            "index"     : idx,
            "value"     : pyo.value(v),
        }
        records.append(record)

    df["model"] = str(records)
    
    row_str = ",".join(f"{k}={v}" for k, v in df.iloc[0].astype(str).items())

    return row_str


def create_tool_calling_agent(
    model: LanguageModelLike,
    tools: Union[ToolNode, Sequence[BaseTool]],
    agent_prompt: Optional[str] = None,
) -> CompiledGraph:
    model = model.bind_tools(tools)

    def routing_logic(state: ChatAgentState):
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            return "continue"
        else:
            return "end"

    if agent_prompt:
        system_message = {"role": "system", "content": agent_prompt}
        preprocessor = RunnableLambda(
            lambda state: [system_message] + state["messages"]
        )
    else:
        preprocessor = RunnableLambda(lambda state: state["messages"])
    model_runnable = preprocessor | model

    def call_model(
        state: ChatAgentState,
        config: RunnableConfig,
    ):
        response = model_runnable.invoke(state, config)

        return {"messages": [response]}

    workflow = StateGraph(ChatAgentState)
    workflow.add_node("agent", RunnableLambda(call_model))
    workflow.add_node("tools", ChatAgentToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        routing_logic,
        {
            "continue": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


class SupplyChainAgent(ChatAgent):
    def __init__(self, config, tools):
        # Load config
        # When this agent is deployed to Model Serving, the configuration loaded here is replaced with the config passed to mlflow.pyfunc.log_model(model_config=...)
        self.config = ModelConfig(development_config=config)
        self.tools = tools
        self.agent = self._build_agent_from_config()

    def _build_agent_from_config(self):
        llm = ChatDatabricks(
            endpoint=self.config.get("endpoint_name"),
            temperature=self.config.get("temperature"),
            max_tokens=self.config.get("max_tokens"),
        )
        agent = create_tool_calling_agent(
            llm,
            tools=self.tools,
            agent_prompt=self.config.get("system_prompt"),
        )
        return agent

    @mlflow.trace(name="SupplyChainAgent", span_type=mlflow.entities.SpanType.AGENT)
    def predict(
        self,
        messages: list[ChatAgentMessage],
        context: Optional[ChatContext] = None,
        custom_inputs: Optional[dict[str, Any]] = None,
    ) -> ChatAgentResponse:
        # ChatAgent has a built-in helper method to help convert framework-specific messages, like langchain BaseMessage to a python dictionary
        request = {"messages": self._convert_messages_to_dict(messages)}

        output = self.agent.invoke(request)
        # Here 'output' is already a ChatAgentResponse, but to make the ChatAgent signature explicit for this demonstration we are returning a new instance
        return ChatAgentResponse(**output)
    
tools = [ttr_agent_tool]

AGENT = SupplyChainAgent(config, tools)
mlflow.models.set_model(AGENT)
