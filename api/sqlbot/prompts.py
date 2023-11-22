from typing import Any

from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import ChatPromptValue, PromptValue
from langchain.schema import AIMessage, ChatMessage, HumanMessage, SystemMessage

SYSTEM_PREFIX = "<|im_start|>system"
SYSTEM_SUFFIX = "<|im_end|>"
HUMAN_PREFIX = "<|im_start|>user"
HUMAN_SUFFIX = "<|im_end|>"
AI_PREFIX = "<|im_start|>assistant"
AI_SUFFIX = "<|im_end|>"


class ChatMLPromptTemplate(ChatPromptTemplate):
    """A prompt template for Chat Markup Language models.
    See <https://github.com/openai/openai-python/blob/main/chatml.md>"""

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        """Format prompt."""
        messages = self.format_messages(**kwargs)
        return ChatMLPromptValue(messages=messages)


class ChatMLPromptValue(ChatPromptValue):
    """Chat Markup Language prompt value.

    A type of a prompt value that is built from messages.
    """

    system_prefix: str = SYSTEM_PREFIX
    system_suffix: str = SYSTEM_SUFFIX
    human_prefix: str = HUMAN_PREFIX
    human_suffix: str = HUMAN_SUFFIX
    ai_prefix: str = AI_PREFIX
    ai_suffix: str = AI_SUFFIX
    prefix_separator: str = "\n"
    """separator between prefix and content"""
    message_separator: str = "\n"
    """separator between messages"""

    def to_string(self) -> str:
        """Return prompt as string."""
        string_messages = []
        for m in self.messages:
            if isinstance(m, HumanMessage):
                prefix = self.human_prefix
                suffix = self.human_suffix
            elif isinstance(m, AIMessage):
                prefix = self.ai_prefix
                suffix = self.ai_suffix
            elif isinstance(m, SystemMessage):
                prefix = self.system_prefix
                suffix = self.system_suffix
            elif isinstance(m, ChatMessage):
                prefix = m.role
                suffix = ""
            else:
                raise ValueError(f"Got unsupported message type: {m}")
            message = f"{prefix}{self.prefix_separator}{m.content}{suffix}"
            if isinstance(m, AIMessage) and "function_call" in m.additional_kwargs:
                message += f"{m.additional_kwargs['function_call']}"
            string_messages.append(message)
        # an empty message indicates that the assistant should start talking
        string_messages.append(f"{self.ai_prefix}{self.prefix_separator}")
        msgs = self.message_separator.join(string_messages)
        return msgs
