from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from aredis_om import JsonModel, Field
from langchain.schema import AgentAction, BaseMessage
from pydantic import BaseModel, root_validator

from sqlbot.utils import utcnow


class IntermediateSteps(BaseModel):
    """Used to serialize list of pydantic models."""

    __root__: list[tuple[AgentAction, Any]]


class ChatMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    """Message id, used to chain stream responses into message."""
    conversation: Optional[str]
    """Conversation id"""
    from_: Optional[str] = Field(alias="from")
    """A transient field to determine conversation id."""
    content: Optional[str]
    type: str
    intermediate_steps: Optional[list[tuple[AgentAction, Any]]] = None
    # sent_at is not an important information for the user, as far as I can tell.
    # But it introduces some complexity in the code, so I'm removing it for now.
    # sent_at: datetime = Field(default_factory=datetime.now)

    @root_validator(pre=True)
    def deser_steps(cls, values):
        if "intermediate_steps" in values and values["intermediate_steps"] is not None:
            values["intermediate_steps"] = IntermediateSteps.parse_raw(
                values["intermediate_steps"]
            ).__root__
        return values

    @staticmethod
    def from_lc(lc_message: BaseMessage, conv_id: str, from_: str) -> "ChatMessage":
        msg_id_str = lc_message.additional_kwargs.get("id", None)
        msg_id = UUID(msg_id_str) if msg_id_str else uuid4()
        steps_str = lc_message.additional_kwargs.get("intermediate_steps", None)
        return ChatMessage(
            id=msg_id,
            conversation=conv_id,
            from_=from_,
            content=lc_message.content,
            type="text",
            intermediate_steps=steps_str,
        )

    _encoders_by_type = {
        datetime: lambda dt: dt.isoformat(timespec="seconds"),
        UUID: lambda uid: uid.hex,
    }

    def _iter(self, **kwargs):
        for key, value in super()._iter(**kwargs):
            yield key, self._encoders_by_type.get(type(value), lambda v: v)(value)

    def dict(
        self, by_alias: bool = True, exclude_none: bool = True, **kwargs
    ) -> dict[str, Any]:
        return super().dict(by_alias=by_alias, exclude_none=exclude_none, **kwargs)

    class Config:
        allow_population_by_field_name = True
        """'from' is a reversed word in python, so we have to populate ChatMessage by 'from_'"""


class Conversation(JsonModel):
    id: Optional[str]
    title: str
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    # TODO: this is not clear as the model will return both a 'pk' and an 'id' with the same value.
    # But I think id is more general than pk.
    @root_validator(pre=True)
    def set_id(cls, values):
        if "pk" in values:
            values["id"] = values["pk"]
        return values


class ConversationDetail(Conversation):
    """Conversation with messages."""

    messages: list[ChatMessage] = []


class UpdateConversation(BaseModel):
    title: str
