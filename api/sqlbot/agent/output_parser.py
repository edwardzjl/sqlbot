import json
import re
from json.decoder import JSONDecodeError
from typing import Union

from langchain.agents.structured_chat.output_parser import StructuredChatOutputParser
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from loguru import logger


class StripFinalAnswerPrefixStructuredChatOutputParser(StructuredChatOutputParser):
    """Output parser for the structured chat agent."""

    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            action_match = self.pattern.search(text)
            if action_match is not None:
                response: dict = json.loads(action_match.group(1).strip(), strict=False)
                if isinstance(response, list):
                    # gpt turbo frequently ignores the directive to emit a single action
                    logger.warning("Got multiple action responses: %s", response)
                    response = response[0]
                if "answer" in response:
                    return AgentFinish({"output": response["answer"]}, text)
                else:
                    tool_name = response.pop("tool_name")
                    # sometimes our LLM will return {"action": $action, "foo": $action_input}
                    if "tool_input" not in response and len(response) > 0:
                        k, v = response.popitem()
                        logger.warning(f"tool_input not found, using {k} as tool_input")
                        tool_input = v
                    else:
                        tool_input = response.get("tool_input", {})
                    return AgentAction(tool_name, tool_input, text)
            else:
                prefix_found = text.find("Final Answer:")
                if prefix_found != -1:
                    return AgentFinish(
                        {"output": text[prefix_found + 13 :].strip()}, text
                    )
                stripped = text.split("```", 1)[0]
                action = json.loads(stripped)
                return AgentAction(action["tool_name"], action["tool_input"], text)
        except JSONDecodeError as e:
            stripped = text.split("```", 1)[0]
            action = json.loads(stripped)
            return AgentAction(action["tool_name"], action["tool_input"], text)
        except Exception as e:
            # raise OutputParserException(f"Could not parse LLM output: {text}") from e
            logger.warning(f"Could not parse LLM output: {text}, error: {str(e)}")
            return AgentFinish({"output": text.strip()}, text)
