from typing import Any, Sequence

from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import ChatPromptValue, PromptValue
from langchain.schema import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
)


class ChatMLPromptTemplate(ChatPromptTemplate):
    """A prompt template for Chat Markup Language models.
    See <https://github.com/openai/openai-python/blob/main/chatml.md>"""

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        """Format prompt."""
        messages = self.format_messages(**kwargs)
        return ChatMLPromptValue(messages=messages)


class ChatMLPromptValue(ChatPromptValue):
    """Chat prompt value.

    A type of a prompt value that is built from messages.
    """

    messages: Sequence[BaseMessage]
    """List of messages."""

    def to_string(self) -> str:
        """Return prompt as string."""
        return f"{get_buffer_string(self.messages)}\n<|im_start|>assistant\n```json\n"

    def to_messages(self) -> list[BaseMessage]:
        """Return prompt as a list of messages."""
        return list(self.messages)


def get_buffer_string(
    messages: Sequence[BaseMessage],
    system_prefix: str = "<|im_start|>system",
    system_suffix: str = "<|im_end|>\n",
    function_prefix: str = "Function",
    function_suffix: str = "",
    human_prefix: str = "<|im_start|>user",
    human_suffix: str = "<|im_end|>",
    ai_prefix: str = "<|im_start|>assistant",
    ai_suffix: str = "<|im_end|>",
    prefix_separator: str = "\n",
    message_separator: str = "\n",
) -> str:
    """Convert sequence of Messages to strings and concatenate them into one string.

    Args:
        messages: Messages to be converted to strings.
        system_prefix: The prefix to prepend to contents of SystemMessages.
        system_suffix: The suffix to append to contents of SystemMessages.
        human_prefix: The prefix to prepend to contents of HumanMessages.
        human_suffix: The suffix to append to contents of HumanMessages.
        ai_prefix: The prefix to prepend to contents of AIMessages.
        ai_suffix: The suffix to append to contents of AIMessages.
        prefix_separator: The separator between message prefix and content.
        message_separator: The separator between messages.

    Returns:
        A single string concatenation of all input messages.

    Example:
        .. code-block:: python

            from langchain.schema import AIMessage, HumanMessage

            messages = [
                HumanMessage(content="Hi, how are you?"),
                AIMessage(content="Good, how are you?"),
            ]
            get_buffer_string(messages)
            # -> "Human: Hi, how are you?\nAI: Good, how are you?"
    """
    string_messages = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = human_prefix
            suffix = human_suffix
        elif isinstance(m, AIMessage):
            role = ai_prefix
            suffix = ai_suffix
        elif isinstance(m, SystemMessage):
            role = system_prefix
            suffix = system_suffix
        elif isinstance(m, FunctionMessage):
            role = function_prefix
            suffix = function_suffix
        elif isinstance(m, ChatMessage):
            role = m.role
        else:
            raise ValueError(f"Got unsupported message type: {m}")
        message = f"{role}{prefix_separator}{m.content}{suffix}"
        if isinstance(m, AIMessage) and "function_call" in m.additional_kwargs:
            message += f"{m.additional_kwargs['function_call']}"
        string_messages.append(message)

    return message_separator.join(string_messages)
