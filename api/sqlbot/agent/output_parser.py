import json
import re
from typing import Union

from langchain.agents.structured_chat.output_parser import StructuredChatOutputParser
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from loguru import logger

from sqlbot.agent.prompts import FORMAT_INSTRUCTIONS


class StripFinalAnswerPrefixStructuredChatOutputParser(StructuredChatOutputParser):
    """Output parser for the structured chat agent."""

    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            action_match = self.pattern.search(text)
            if action_match is not None:
                response: dict = json.loads(action_match.group(1).strip(), strict=False)
                if isinstance(response, list):
                    # gpt turbo frequently ignores the directive to emit a single action
                    logger.warning("Got multiple action responses: %s", response)
                    response = response[0]
                if response["action"] == "Final Answer":
                    return AgentFinish({"output": response["action_input"]}, text)
                else:
                    action = response.pop("action")
                    # sometimes our LLM will return {"action": $action, "foo": $action_input}
                    if "action_input" not in response and len(response) > 0:
                        k, v = response.popitem()
                        logger.warning(
                            f"action_input not found, using {k} as action_input"
                        )
                        action_input = v
                    else:
                        action_input = response.get("action_input", {})
                    return AgentAction(action, action_input, text)
            else:
                prefix_found = text.find("Final Answer:")
                if prefix_found != -1:
                    return AgentFinish(
                        {"output": text[prefix_found + 13 :].strip()}, text
                    )
                return AgentFinish({"output": text.strip()}, text)
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e
