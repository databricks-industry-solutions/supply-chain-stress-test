# Databricks notebook source
# MAGIC %pip install -U -qqqq mlflow langchain langgraph==0.3.4 databricks-langchain pydantic databricks-agents unitycatalog-langchain[databricks]
# MAGIC %pip install -r ../requirements.txt --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %%writefile supply_chain_agent.py
# MAGIC from typing import Any, Optional, Sequence, Union
# MAGIC import os
# MAGIC import json
# MAGIC import mlflow
# MAGIC import pandas as pd
# MAGIC from databricks_langchain import ChatDatabricks
# MAGIC from databricks_langchain import (
# MAGIC     DatabricksFunctionClient,
# MAGIC     UCFunctionToolkit,
# MAGIC     set_uc_function_client,
# MAGIC )
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC from langchain_core.language_models import LanguageModelLike
# MAGIC from langchain_core.runnables import RunnableConfig, RunnableLambda
# MAGIC from langchain_core.tools import BaseTool, tool
# MAGIC from langgraph.graph import END, StateGraph
# MAGIC from langgraph.graph.graph import CompiledGraph
# MAGIC from langgraph.prebuilt.tool_node import ToolNode
# MAGIC from mlflow.langchain.chat_agent_langgraph import ChatAgentState, ChatAgentToolNode
# MAGIC from mlflow.models import ModelConfig
# MAGIC from mlflow.pyfunc import ChatAgent
# MAGIC from mlflow.types.agent import (
# MAGIC     ChatAgentMessage,
# MAGIC     ChatAgentResponse,
# MAGIC     ChatContext,
# MAGIC )
# MAGIC
# MAGIC import random, string, math
# MAGIC from itertools import product
# MAGIC from collections import defaultdict
# MAGIC import pyomo.environ as pyo
# MAGIC import scripts.utils as utils
# MAGIC
# MAGIC
# MAGIC mlflow.langchain.autolog()
# MAGIC
# MAGIC LLM_ENDPOINT = "databricks-llama-4-maverick"
# MAGIC config = {
# MAGIC     "endpoint_name": LLM_ENDPOINT,
# MAGIC     "catalog": "supply_chain_stress_test",
# MAGIC     "database": "data",
# MAGIC     "volume": "operational",
# MAGIC     "temperature": 0.01,
# MAGIC     "max_tokens": 1000,
# MAGIC     "system_prompt": """
# MAGIC     "You are a helpful assistant that answers questions about a supply chain network. Questions outside this topic are considered irrelevant. You use a set of tools to provide answers, and if needed, you ask the user follow up questions to clarify their request.
# MAGIC
# MAGIC     Below are the definitions of the model parameters:
# MAGIC     Parameters            | What it represents                                                                              --------------------- | -------------------------------------------------------------------------------------------------- | tier1 / tier2 / tier3 | Lists of node IDs in each tier.                                                                    |edges                 | Directed links `(source, target)` showing which node supplies which.                               |material_type         | List of all material types.                                                                        |
# MAGIC     supplier_material_type| Material type each supplier produces and supplies.                                                 |
# MAGIC     f                     | Profit margin for each Tier 1 node’s finished product.                                             |
# MAGIC     s                     | On-hand inventory units at every node.                                                             |
# MAGIC     d                     | Demand per time unit for Tier 1 products.                                                          |
# MAGIC     c                     | Production capacity per time unit at each node.                                                    |
# MAGIC     r                     | Number of material types (k) required to make one unit of node j.                                  |
# MAGIC     N_minus               | For each node j (Tier 1 or 2), the set of material types it requires.                              |
# MAGIC     N_plus                | For each supplier i (Tier 2 or 3), the set of downstream nodes j it feeds.                         |
# MAGIC     P                     | For each (j, material_part) pair, a list of upstream suppliers i that provides it (multi-sourcing view). |
# MAGIC     
# MAGIC     And the definitions of decision variables:
# MAGIC     Decision Variables    | What it represents                                                                              --------------------- | -------------------------------------------------------------------------------------------------- | 
# MAGIC     l                     | Production volume lost of the product of the node.                                                 |u                     | Total production volume of the node during the ttr.                                                |y                     | Allocation of upstream node to downsteam node during the ttr.                                      |
# MAGIC     
# MAGIC     Do not forget to report the profit loss during the recovery period. When providing recommendations, base them on the interpretation of the decision variables and summarize the best actions for this scenario. Provide precise numbers whenever possible.
# MAGIC     """,
# MAGIC }
# MAGIC
# MAGIC @tool
# MAGIC @mlflow.trace(name="TTR", span_type=mlflow.entities.SpanType.TOOL)
# MAGIC def ttr_agent_tool(
# MAGIC     disrupted: list[str],
# MAGIC     ttr: float,
# MAGIC     catalog: str = config["catalog"],
# MAGIC     database: str = config["database"],
# MAGIC     volume: str = config["volume"],
# MAGIC     ) -> str:
# MAGIC     """
# MAGIC     Runs an optimization algorithm for a given disrupted scenario and returns the results as a string.
# MAGIC
# MAGIC     Parameters:
# MAGIC     disrupted (list[str]): List of disrupted nodes in the scenario.
# MAGIC     ttr (float): Time to recover (TTR) for the disruption scenario.
# MAGIC     catalog (str): Catalog name for Unity Catalog.
# MAGIC     database (str): Database name in Unity Catalog.
# MAGIC     volume (str): Volume name in Unity Catalog.
# MAGIC     
# MAGIC     Returns:
# MAGIC     str: A string representation of the optimization results.
# MAGIC     """    
# MAGIC     # Get the operational data from Unity Catalog Volume
# MAGIC     w = WorkspaceClient(host=os.getenv("HOST"), token=os.getenv("TOKEN"))
# MAGIC     path = f'/Volumes/{catalog}/{database}/{volume}/dataset_small.json'
# MAGIC     resp = w.files.download(path)  # returns DownloadResponse with a BinaryIO at .contents
# MAGIC     with resp.contents as fh:
# MAGIC         dataset = json.load(fh)   # `data` is now a Python dict/list
# MAGIC
# MAGIC     # Build and solve TTR
# MAGIC     df = utils.build_and_solve_ttr(dataset, disrupted, ttr, True)
# MAGIC     model = df["model"].values[0]
# MAGIC     records = []
# MAGIC     for v in model.component_data_objects(ctype=pyo.Var, active=True):
# MAGIC         idx  = v.index()
# MAGIC         record  = {
# MAGIC             "var_name"  : v.parent_component().name,
# MAGIC             "index"     : idx,
# MAGIC             "value"     : pyo.value(v),
# MAGIC         }
# MAGIC         records.append(record)
# MAGIC
# MAGIC     df["model"] = str(records)
# MAGIC     
# MAGIC     row_str = ",".join(f"{k}={v}" for k, v in df.iloc[0].astype(str).items())
# MAGIC
# MAGIC     return row_str
# MAGIC
# MAGIC
# MAGIC def create_tool_calling_agent(
# MAGIC     model: LanguageModelLike,
# MAGIC     tools: Union[ToolNode, Sequence[BaseTool]],
# MAGIC     agent_prompt: Optional[str] = None,
# MAGIC ) -> CompiledGraph:
# MAGIC     model = model.bind_tools(tools)
# MAGIC
# MAGIC     def routing_logic(state: ChatAgentState):
# MAGIC         last_message = state["messages"][-1]
# MAGIC         if last_message.get("tool_calls"):
# MAGIC             return "continue"
# MAGIC         else:
# MAGIC             return "end"
# MAGIC
# MAGIC     if agent_prompt:
# MAGIC         system_message = {"role": "system", "content": agent_prompt}
# MAGIC         preprocessor = RunnableLambda(
# MAGIC             lambda state: [system_message] + state["messages"]
# MAGIC         )
# MAGIC     else:
# MAGIC         preprocessor = RunnableLambda(lambda state: state["messages"])
# MAGIC     model_runnable = preprocessor | model
# MAGIC
# MAGIC     def call_model(
# MAGIC         state: ChatAgentState,
# MAGIC         config: RunnableConfig,
# MAGIC     ):
# MAGIC         response = model_runnable.invoke(state, config)
# MAGIC
# MAGIC         return {"messages": [response]}
# MAGIC
# MAGIC     workflow = StateGraph(ChatAgentState)
# MAGIC     workflow.add_node("agent", RunnableLambda(call_model))
# MAGIC     workflow.add_node("tools", ChatAgentToolNode(tools))
# MAGIC     workflow.set_entry_point("agent")
# MAGIC     workflow.add_conditional_edges(
# MAGIC         "agent",
# MAGIC         routing_logic,
# MAGIC         {
# MAGIC             "continue": "tools",
# MAGIC             "end": END,
# MAGIC         },
# MAGIC     )
# MAGIC     workflow.add_edge("tools", "agent")
# MAGIC
# MAGIC     return workflow.compile()
# MAGIC
# MAGIC
# MAGIC class SupplyChainAgent(ChatAgent):
# MAGIC     def __init__(self, config, tools):
# MAGIC         # Load config
# MAGIC         # When this agent is deployed to Model Serving, the configuration loaded here is replaced with the config passed to mlflow.pyfunc.log_model(model_config=...)
# MAGIC         self.config = ModelConfig(development_config=config)
# MAGIC         self.tools = tools
# MAGIC         self.agent = self._build_agent_from_config()
# MAGIC
# MAGIC     def _build_agent_from_config(self):
# MAGIC         llm = ChatDatabricks(
# MAGIC             endpoint=self.config.get("endpoint_name"),
# MAGIC             temperature=self.config.get("temperature"),
# MAGIC             max_tokens=self.config.get("max_tokens"),
# MAGIC         )
# MAGIC         agent = create_tool_calling_agent(
# MAGIC             llm,
# MAGIC             tools=self.tools,
# MAGIC             agent_prompt=self.config.get("system_prompt"),
# MAGIC         )
# MAGIC         return agent
# MAGIC
# MAGIC     @mlflow.trace(name="SupplyChainAgent", span_type=mlflow.entities.SpanType.AGENT)
# MAGIC     def predict(
# MAGIC         self,
# MAGIC         messages: list[ChatAgentMessage],
# MAGIC         context: Optional[ChatContext] = None,
# MAGIC         custom_inputs: Optional[dict[str, Any]] = None,
# MAGIC     ) -> ChatAgentResponse:
# MAGIC         # ChatAgent has a built-in helper method to help convert framework-specific messages, like langchain BaseMessage to a python dictionary
# MAGIC         request = {"messages": self._convert_messages_to_dict(messages)}
# MAGIC
# MAGIC         output = self.agent.invoke(request)
# MAGIC         # Here 'output' is already a ChatAgentResponse, but to make the ChatAgent signature explicit for this demonstration we are returning a new instance
# MAGIC         return ChatAgentResponse(**output)
# MAGIC     
# MAGIC tools = [ttr_agent_tool]
# MAGIC
# MAGIC AGENT = SupplyChainAgent(config, tools)
# MAGIC mlflow.models.set_model(AGENT)

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os
import mlflow
from dbruntime.databricks_repl_context import get_context

user = spark.sql('select current_user() as user').collect()[0]['user'] # User email address

# TODO: set WORKSPACE_URL manually if it cannot be inferred from the current notebook
WORKSPACE_URL = None
if WORKSPACE_URL is None:
  workspace_url_hostname = get_context().workspaceUrl
  assert workspace_url_hostname is not None, "Unable to look up current workspace URL. This can happen if running against serverless compute. Manually set WORKSPACE_URL yourself above, or run this notebook against classic compute"
  WORKSPACE_URL = f"https://{workspace_url_hostname}"

# TODO: set secret_scope_name and secret_key_name to access your PAT
secret_scope = "<your_secret_scope>"
secret_key = "<your_secret_key>"

os.environ["HOST"] = WORKSPACE_URL
os.environ["TOKEN"] = dbutils.secrets.get(scope=secret_scope, key=secret_key)

# COMMAND ----------

from supply_chain_agent import AGENT

AGENT.predict({"messages": [{"role": "user", "content": "Tell me what happens if T2_8 is disrupted and requires 9 to recover to its normal state and what to do."}]})

# COMMAND ----------

AGENT.predict({"messages": [{"role": "user", "content": "There has been an incident at T3_15 and it will not be able to supply materials for at least the next 10 time units. Tell me what to do."}]})

# COMMAND ----------

import os
import mlflow
from supply_chain_agent import LLM_ENDPOINT, config, tools
from mlflow.models.resources import DatabricksFunction, DatabricksServingEndpoint
from unitycatalog.ai.langchain.toolkit import UnityCatalogTool

resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)]
for tool in tools:
    if isinstance(tool, UnityCatalogTool):
        resources.append(DatabricksFunction(function_name=tool.uc_function_name))

code_path = os.getcwd().replace("agent", "scripts")

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        python_model="supply_chain_agent.py",
        name="agent",
        model_config=config,
        resources=resources,
        pip_requirements=[
            "mlflow",
            "langchain",
            "langgraph==0.3.4",
            "databricks-langchain",
            "unitycatalog-langchain[databricks]",
            "pydantic",
            "-r ../requirements.txt",
        ],
        code_paths=[code_path],
        input_example={
            "messages": [{"role": "user", "content": "Tell me what happens if T2_8 is disrupted and requires 9 to recover to its normal state and what to do."}]
        },
    )

# COMMAND ----------

import mlflow
from databricks import agents

# Connect to the Unity catalog model registry
mlflow.set_registry_uri("databricks-uc")

catalog = "supply_chain_stress_test"  # Change here
schema = "agents"                     # Change here

# Make sure that the catalog, the schema and the volume exist
_ = spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}") 
_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}") 

# COMMAND ----------

UC_MODEL_NAME = f"{catalog}.{schema}.supply_chain_agent"

# Register to Unity catalog
uc_registered_model_info = mlflow.register_model(
    model_uri=model_info.model_uri, name=UC_MODEL_NAME
)
# Deploy to enable the review app and create an API endpoint
deployment_info = agents.deploy(
    UC_MODEL_NAME, 
    uc_registered_model_info.version,
    environment_vars={
        "HOST": f"{WORKSPACE_URL}",
        "TOKEN": f"{{{{secrets/{secret_scope}/{secret_key}}}}}",
    },
)
