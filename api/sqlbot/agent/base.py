"""SQL agent."""
from typing import Any, Dict, List, Optional

from langchain.agents.agent import AgentExecutor
from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.llm import LLMChain
from langchain.schema.language_model import BaseLanguageModel


from sqlbot.agent.prompts import SQL_PREFIX, SQL_SUFFIX, FORMAT_INSTRUCTIONS
from sqlbot.agent.toolkit import CustomSQLDatabaseToolkit


def create_sql_agent(
    llm: BaseLanguageModel,
    toolkit: CustomSQLDatabaseToolkit,
    callback_manager: Optional[BaseCallbackManager] = None,
    input_variables: Optional[List[str]] = None,
    top_k: int = 10,
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs: Dict[str, Any],
) -> AgentExecutor:
    """Construct an SQL agent from an LLM and tools."""
    tools = toolkit.get_tools()
    prefix = SQL_PREFIX.format(dialect=toolkit.dialect, top_k=top_k)

    prompt = StructuredChatAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=SQL_SUFFIX,
        format_instructions=FORMAT_INSTRUCTIONS,
        input_variables=input_variables,
    )
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        callback_manager=callback_manager,
    )
    tool_names = [tool.name for tool in tools]
    agent = StructuredChatAgent(llm_chain=llm_chain, allowed_tools=tool_names, **kwargs)

    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        **(agent_executor_kwargs or {}),
    )
