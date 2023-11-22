"""SQL agent."""
import json
from typing import Any, Optional, Sequence

from langchain.agents.agent import Agent, AgentExecutor, AgentOutputParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain.schema import (
    AgentAction,
    AgentFinish,
    AIMessage,
    BaseMessage,
    BasePromptTemplate,
    SystemMessage,
)
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool
from pydantic.v1 import Field

from sqlbot.agent.output_parser import JsonOutputParser
from sqlbot.agent.prompts import SYSTEM, TOOLS
from sqlbot.agent.toolkit import SQLBotToolkit
from sqlbot.prompts import ChatMLPromptTemplate
from sqlbot.schemas import IntermediateSteps


class AppendThoughtAgent(Agent):
    output_parser: Optional[AgentOutputParser] = Field(default_factory=JsonOutputParser)

    @classmethod
    def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
        tool_descs = "\n".join([f"{tool.description}" for tool in tools])
        tool_strings = TOOLS.format(tools=tool_descs)
        system_prompt = PromptTemplate(
            template=SYSTEM,
            input_variables=["date"],
            partial_variables={"tools": tool_strings},
        )
        messages = [
            SystemMessagePromptTemplate(prompt=system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
        return ChatMLPromptTemplate(
            input_variables=["date", "input", "agent_scratchpad"], messages=messages
        )

    def _construct_scratchpad(
        self, intermediate_steps: list[tuple[AgentAction, str]]
    ) -> list[BaseMessage]:
        steps = []
        for action, observation in intermediate_steps:
            # action.log contains too much noise
            # maybe I should construct a pydantic model for `action_taken`
            # action_taken = {"tool_name": action.tool, "tool_input": action.tool_input}
            steps.append(AIMessage(content=action.log))
            steps.append(SystemMessage(content=observation))
        return steps

    @classmethod
    def _get_default_output_parser(cls, **kwargs: Any) -> AgentOutputParser:
        """Get default output parser for this class."""
        return JsonOutputParser()

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "<|im_start|>system observation\n"

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the LLM call with."""
        return "<|im_start|>assistant\n"

    def return_stopped_response(
        self,
        early_stopping_method: str,
        intermediate_steps: list[tuple[AgentAction, str]],
        **kwargs: Any,
    ) -> AgentFinish:
        """Return response when agent has been stopped due to max iterations."""
        if early_stopping_method == "force":
            # `force` just returns a constant string
            return AgentFinish(
                {
                    "output": "Agent stopped due to iteration limit or time limit.",
                    "reason": "early_stopped",
                },
                "",
            )
        elif early_stopping_method == "generate":
            # Generate does one final forward pass
            thoughts = ""
            for action, observation in intermediate_steps:
                thoughts += action.log
                thoughts += (
                    f"\n{self.observation_prefix}{observation}\n{self.llm_prefix}"
                )
            # Adding to the previous steps, we now tell the LLM to make a final pred
            thoughts += (
                "\n\nI now need to return a final answer based on the previous steps:"
            )
            new_inputs = {"agent_scratchpad": thoughts, "stop": self._stop}
            full_inputs = {**kwargs, **new_inputs}
            full_output = self.llm_chain.predict(**full_inputs)
            # We try to extract a final answer
            parsed_output = self.output_parser.parse(full_output)
            if isinstance(parsed_output, AgentFinish):
                # If we can extract, we send the correct stuff
                return parsed_output
            else:
                # If we can extract, but the tool is not the final tool,
                # we just return the full output
                return AgentFinish(
                    {"output": full_output, "reason": "early_stopped"}, full_output
                )
        else:
            raise ValueError(
                "early_stopping_method should be one of `force` or `generate`, "
                f"got {early_stopping_method}"
            )


class CustomAgentExecutor(AgentExecutor):
    def prep_inputs(self, inputs: dict[str, Any] | Any) -> dict[str, str]:
        inputs = super().prep_inputs(inputs)
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            self.memory.chat_memory.add_user_message(inputs[self.memory.input_key])
        return inputs

    def prep_outputs(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        return_only_outputs: bool = False,
    ) -> dict[str, str]:
        """disable persist history"""
        self._validate_outputs(outputs)
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            additional_kwargs = {}
            if "intermediate_steps" in outputs:
                wrap = IntermediateSteps.model_validate(outputs["intermediate_steps"])
                additional_kwargs["intermediate_steps"] = wrap.model_dump_json()
            msg = AIMessage(
                content=outputs[self.memory.output_key],
                additional_kwargs=additional_kwargs,
            )
            self.memory.chat_memory.add_message(msg)
        if return_only_outputs:
            return outputs
        else:
            return {**inputs, **outputs}


def create_sql_agent(
    llm: BaseLanguageModel,
    toolkit: SQLBotToolkit,
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[dict[str, Any]] = None,
    **kwargs: dict[str, Any],
) -> AgentExecutor:
    """Construct an SQL agent from an LLM and tools."""
    tools = toolkit.get_tools()

    agent = AppendThoughtAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        **kwargs,
    )

    return CustomAgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        **(agent_executor_kwargs or {}),
    )
