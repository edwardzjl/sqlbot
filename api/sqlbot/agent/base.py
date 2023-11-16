"""SQL agent."""
from typing import Any, Optional, Sequence
from uuid import uuid4

from langchain.agents.agent import AgentExecutor
from langchain.agents.structured_chat.base import (
    HUMAN_MESSAGE_TEMPLATE,
    StructuredChatAgent,
)
from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.llm import LLMChain
from langchain.memory.chat_memory import BaseChatMemory
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain.schema import AgentAction, AgentFinish, AIMessage, BasePromptTemplate
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool

from sqlbot.agent.output_parser import StripFinalAnswerPrefixStructuredChatOutputParser
from sqlbot.agent.prompts import FORMAT_INSTRUCTIONS, PREFIX, SUFFIX
from sqlbot.agent.toolkit import SQLBotToolkit
from sqlbot.schemas import IntermediateSteps
from sqlbot.utils import utcnow


class AppendThoughtAgent(StructuredChatAgent):
    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        prefix: str = PREFIX,
        suffix: str = SUFFIX,
        human_message_template: str = HUMAN_MESSAGE_TEMPLATE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[list[str]] = None,
    ) -> BasePromptTemplate:
        tool_strings = "\n".join(
            [f"> {tool.name}: {tool.description}" for tool in tools]
        )
        tool_names = ", ".join([tool.name for tool in tools])
        format_instructions = format_instructions.format(tool_names=tool_names)
        template = "\n\n".join([prefix, tool_strings, format_instructions, suffix])
        if input_variables is None:
            input_variables = ["input", "agent_scratchpad"]
        messages = [
            SystemMessagePromptTemplate.from_template(template),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template(human_message_template),
        ]
        return ChatPromptTemplate(input_variables=input_variables, messages=messages)

    def _construct_scratchpad(
        self, intermediate_steps: list[tuple[AgentAction, str]]
    ) -> str:
        agent_scratchpad = super(StructuredChatAgent, self)._construct_scratchpad(
            intermediate_steps
        )
        # agent_scratchpad = Agent._construct_scratchpad(intermediate_steps)
        if not isinstance(agent_scratchpad, str):
            raise ValueError("agent_scratchpad should be of type string.")
        if agent_scratchpad:
            return (
                f"This was your previous work "
                f"(but I haven't seen any of it! I only see what "
                f"you return as final answer):\n{self.llm_prefix}{agent_scratchpad}"
            )
        else:
            return self.llm_prefix

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
    callback_manager: Optional[BaseCallbackManager] = None,
    input_variables: Optional[list[str]] = None,
    top_k: int = 10,
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[dict[str, Any]] = None,
    **kwargs: dict[str, Any],
) -> AgentExecutor:
    """Construct an SQL agent from an LLM and tools."""
    tools = toolkit.get_tools()
    prefix = PREFIX.format(dialect=toolkit.dialect, top_k=top_k)
    suffix = SUFFIX.format(dialect=toolkit.dialect)

    prompt = AppendThoughtAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=suffix,
        format_instructions=FORMAT_INSTRUCTIONS,
        input_variables=input_variables,
    )
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        callback_manager=callback_manager,
    )
    tool_names = [tool.name for tool in tools]
    output_parser = StructuredChatOutputParserWithRetries(
        base_parser=StripFinalAnswerPrefixStructuredChatOutputParser()
    )
    agent = AppendThoughtAgent(
        llm_chain=llm_chain,
        allowed_tools=tool_names,
        output_parser=output_parser,
        **kwargs,
    )

    return CustomAgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        **(agent_executor_kwargs or {}),
    )
